import React, { useState, useMemo } from 'react';
import { fileService } from '../services/fileService';
import { File as FileType } from '../types/file';
import { DocumentIcon, TrashIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export const FileList: React.FC = () => {
  const queryClient = useQueryClient();

  const [searchTerm, setSearchTerm] = useState('');
  const [fileType, setFileType] = useState('');
  const [minSize, setMinSize] = useState('');
  const [maxSize, setMaxSize] = useState('');
  const [uploadDate, setUploadDate] = useState('');
  // Query for fetching files
  const { data: files, isLoading, error } = useQuery({
    queryKey: ['files'],
    queryFn: fileService.getFiles,
  });

  // Mutation for deleting files
  const deleteMutation = useMutation({
    mutationFn: fileService.deleteFile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
    },
  });

  // Mutation for downloading files
  const downloadMutation = useMutation({
    mutationFn: ({ fileUrl, filename }: { fileUrl: string; filename: string }) =>
      fileService.downloadFile(fileUrl, filename),
  });

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const handleDownload = async (fileUrl: string, filename: string) => {
    try {
      await downloadMutation.mutateAsync({ fileUrl, filename });
    } catch (err) {
      console.error('Download error:', err);
    }
  };

  const filteredFiles = useMemo(() => {
    if (!files) return [];

    return files.filter((file: FileType) => {
      const matchesSearch = file.original_filename
        .toLowerCase()
        .includes(searchTerm.toLowerCase());

      const matchesType = fileType ? file.file_type === fileType : true;

      const matchesSize =
        (!minSize || file.size >= parseInt(minSize) * 1024) &&
        (!maxSize || file.size <= parseInt(maxSize) * 1024);

      const matchesDate = uploadDate
        ? new Date(file.uploaded_at).toISOString().split('T')[0] === uploadDate
        : true;

      return matchesSearch && matchesType && matchesSize && matchesDate;
    });
  }, [files, searchTerm, fileType, minSize, maxSize, uploadDate]);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="space-y-3">
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">Failed to load files. Please try again.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Uploaded Files</h2>

      {/* Search + Filters */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
        <input
          type="text"
          placeholder="Search by filename..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="border p-2 rounded-md w-full"
        />

        <select
          value={fileType}
          onChange={(e) => setFileType(e.target.value)}
          className="border p-2 rounded-md w-full"
        >
          <option value="">All Types</option>
          <option value="pdf">PDF</option>
          <option value="jpg">JPG</option>
          <option value="png">PNG</option>
          <option value="txt">TXT</option>
        </select>

        <div className="flex space-x-2">
          <input
            type="number"
            placeholder="Min KB"
            value={minSize}
            onChange={(e) => setMinSize(e.target.value)}
            className="border p-2 rounded-md w-full"
          />
          <input
            type="number"
            placeholder="Max KB"
            value={maxSize}
            onChange={(e) => setMaxSize(e.target.value)}
            className="border p-2 rounded-md w-full"
          />
        </div>

        <input
          type="date"
          value={uploadDate}
          onChange={(e) => setUploadDate(e.target.value)}
          className="border p-2 rounded-md w-full"
        />
      </div>

      {!filteredFiles || filteredFiles.length === 0 ? (
        <div className="text-center py-12">
          <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No files found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Try adjusting your search or filters
          </p>
        </div>
      ) : (
        <div className="mt-6 flow-root">
          <ul className="-my-5 divide-y divide-gray-200">
            {filteredFiles.map((file) => (
              <li key={file.id} className="py-4">
                <div className="flex items-center space-x-4">
                  <DocumentIcon className="h-8 w-8 text-gray-400" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.original_filename}
                    </p>
                    <p className="text-sm text-gray-500">
                      {file.file_type} • {(file.size / 1024).toFixed(2)} KB
                    </p>
                    <p className="text-sm text-gray-500">
                      Uploaded {new Date(file.uploaded_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleDownload(file.file, file.original_filename)}
                      disabled={downloadMutation.isPending}
                      className="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm rounded-md text-white bg-primary-600 hover:bg-primary-700"
                    >
                      <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                      Download
                    </button>
                    <button
                      onClick={() => handleDelete(file.id)}
                      disabled={deleteMutation.isPending}
                      className="inline-flex items-center px-3 py-2 border border-transparent shadow-sm text-sm rounded-md text-white bg-red-600 hover:bg-red-700"
                    >
                      <TrashIcon className="h-4 w-4 mr-1" />
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};