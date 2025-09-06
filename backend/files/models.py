import os
import uuid
import hashlib
import mimetypes
from datetime import datetime

from django.db import models, IntegrityError, transaction
from django.core.files.storage import default_storage
from django.utils.timezone import now


def sha256_of_file(file_obj):
    """Compute sha256 of a Django uploaded file in chunks; preserve stream position."""
    hasher = hashlib.sha256()
    # try streaming over .chunks() (works for UploadedFile)
    try:
        for chunk in file_obj.chunks():
            hasher.update(chunk)
    except Exception:
        # fallback: read whole file (rare), but ensure we reset afterwards
        file_obj.seek(0)
        hasher.update(file_obj.read())
    # reset file pointer for later saving
    try:
        file_obj.seek(0)
    except Exception:
        pass
    return hasher.hexdigest()


def upload_path_for_hash(sha256_hex, original_name):
    ext = os.path.splitext(original_name)[1]  # includes dot if present
    dt = now()
    return os.path.join('uploads', str(dt.year), str(dt.month), sha256_hex + ext)

class StorageStats(models.Model):
    total_saved_bytes = models.BigIntegerField(default=0)

    @classmethod
    def add_savings(cls, bytes_saved):
        obj, _ = cls.objects.get_or_create(id=1)  # singleton row
        obj.total_saved_bytes += bytes_saved
        obj.save()
        return obj.total_saved_bytes


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='uploads/temp')  # temporary; we'll move/rename in save()
    sha256 = models.CharField(max_length=64, unique=True, db_index=True)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100, blank=True, null=True)
    size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_filename

    def compute_hash_and_prepare(self):
        """
        Ensure sha256, file.name (target path), file_type and size are set.
        This function is idempotent and safe to call even if sha256 is already present.
        """
        if not self.file:
            return

        # Compute sha only if missing (avoid extra work), but always ensure size/file_type/name are set.
        if not getattr(self, "sha256", None):
            self.sha256 = sha256_of_file(self.file)

        # derive path and metadata
        target_name = upload_path_for_hash(
            self.sha256, self.original_filename or self.file.name
        )
        self.file_type = self.file_type or (
            mimetypes.guess_type(self.original_filename or self.file.name)[0] or ""
        )

        # If storage already has the file under target_name, point to it and set size from storage
        if default_storage.exists(target_name):
            self.file.name = target_name
            try:
                self.size = default_storage.size(target_name)
            except Exception:
                self.size = getattr(self.file, "size", None) or 0
            return

        # else set name so storage will save it to the desired path
        self.file.name = target_name

        # ensure size is set from uploaded file if possible
        try:
            self.size = self.size or getattr(self.file, "size", None) or 0
        except Exception:
            try:
                self.file.seek(0)
                b = self.file.read()
                self.size = len(b)
                self.file.seek(0)
            except Exception:
                self.size = self.size or 0

    def save(self, *args, **kwargs):
        # Always compute/prepare metadata if a file is attached
        if self.file:
            self.compute_hash_and_prepare()

        # Save row. Use DB-level unique constraint + atomic block to avoid duplicates on race.
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError as exc:
            # Only treat as duplicate if a row actually exists with that sha256.
            # If not, re-raise the original exception so the real problem surfaces.
            try:
                existing = File.objects.get(sha256=self.sha256)
            except File.DoesNotExist:
                # Not a duplicate — re-raise the original IntegrityError
                raise
            else:
                # Duplicate created concurrently; sync fields to existing
                self.id = existing.id
                self.file = existing.file
                self.original_filename = existing.original_filename
                self.file_type = existing.file_type
                self.size = existing.size
                self.uploaded_at = existing.uploaded_at