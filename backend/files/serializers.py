from rest_framework import serializers
from .models import File, sha256_of_file
import hashlib


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ('id', 'file', 'original_filename', 'file_type', 'size', 'sha256', 'uploaded_at')
        read_only_fields = ('sha256', 'size', 'file_type', 'uploaded_at', 'id')

    def create(self, validated_data, **kwargs):
        """
        Accepts optional sha256 via kwargs to avoid rehashing in cases where the view already computed it.
        If sha256 provided and an existing file exists, return that existing instance.
        """
        uploaded = validated_data.get('file')
        orig_name = validated_data.get('original_filename') or getattr(uploaded, 'name', '')
        sha = kwargs.get('sha256')

        # compute sha if not provided
        if sha is None:
            try:
                sha = sha256_of_file(uploaded)
            except Exception:
                uploaded.seek(0)
                sha = hashlib.sha256(uploaded.read()).hexdigest()
                uploaded.seek(0)

        # If exists, return existing instance (avoid duplicate DB row)
        existing = File.objects.filter(sha256=sha).first()
        if existing:
            return existing

        # Create instance, prefill sha so model.save doesn't recompute unnecessarily
        file_obj = File(file=uploaded, original_filename=orig_name)
        file_obj.sha256 = sha
        file_obj.save()
        return file_obj
