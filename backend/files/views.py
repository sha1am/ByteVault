# files/views.py
from django.db import transaction
from django.core.files.storage import default_storage

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .models import File, sha256_of_file, StorageStats
from .serializers import FileSerializer
from rest_framework.decorators import action, api_view  


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # compute sha once (chunked, resets file pointer)
        try:
            sha = sha256_of_file(file_obj)
        except Exception:
            file_obj.seek(0)
            import hashlib
            sha = hashlib.sha256(file_obj.read()).hexdigest()
            file_obj.seek(0)

        # If file with same sha exists, return it (duplicate)
        existing = File.objects.filter(sha256=sha).first()
        if existing:
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Create new
        data = {
            'file': file_obj,
            'original_filename': file_obj.name,
            'file_type': getattr(file_obj, 'content_type', None),
            'size': getattr(file_obj, 'size', None) or 0
        }

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        # pass sha to serializer.create to avoid rehashing
        instance = serializer.save(sha256=sha)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a File record and delete the underlying stored file only if no other DB
        record references the same sha256. Uses default_storage so this works for local
        filesystem or remote storages (S3) transparently.
        """
        instance = self.get_object()  # raises 404 if not found

        storage_name = instance.file.name if instance.file else None
        sha = instance.sha256

        # Delete DB row inside atomic block, then delete stored file if no remaining references
        with transaction.atomic():
            self.perform_destroy(instance)

            # If there are other File rows sharing the same sha, don't delete the stored blob
            if sha and File.objects.filter(sha256=sha).exists():
                return Response(status=status.HTTP_204_NO_CONTENT)

        # No DB record references the sha any more — delete the stored blob
        if storage_name:
            try:
                default_storage.delete(storage_name)
            except Exception:
                # In dev we silently ignore storage deletion errors.
                # In prod: log and/or enqueue retry job.
                pass

        return Response(status=status.HTTP_204_NO_CONTENT)
    @action(detail=False, methods=["get"])
    def check(self, request):
        """
        Check if a file with the given sha already exists.
        If yes → record savings in StorageStats.
        """
        sha = request.query_params.get("sha")
        if not sha:
            return Response({"detail": "missing sha"}, status=status.HTTP_400_BAD_REQUEST)

        existing = File.objects.filter(sha256=sha).first()
        if existing:
            # Add savings: pretend we skipped re-uploading this file
            if existing.size:
                stats, _ = StorageStats.objects.get_or_create(id=1)
                stats.total_saved_bytes += existing.size
                stats.save()

            serializer = self.get_serializer(existing)
            return Response(
                {
                    **serializer.data,
                    "duplicate": True,
                    "saved_bytes": existing.size,
                },
                status=status.HTTP_200_OK,
            )

        return Response({"duplicate": False}, status=status.HTTP_404_NOT_FOUND)

    def upload_file(request):
        uploaded_file = request.FILES["file"]
        file_size = uploaded_file.size
        file_hash = calculate_hash(uploaded_file)

        existing = File.objects.filter(checksum=file_hash).first()
        if existing:
            # Duplicate found → add to savings
            StorageStats.add_savings(file_size)
            return Response({"detail": "Duplicate file skipped", "saved_bytes": file_size}, status=200)

        # Else proceed normally
        new_file = File.objects.create(file=uploaded_file, checksum=file_hash, size=file_size)
        return Response({"id": new_file.id}, status=201)
@api_view(["GET"])
def get_storage_savings(request):
    stats, _ = StorageStats.objects.get_or_create(id=1)
    return Response({"total_saved_bytes": stats.total_saved_bytes})
