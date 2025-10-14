import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../contexts/AuthContext";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function FileList({ refreshTrigger }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { token } = useAuth();

  const fetchFiles = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/files`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setFiles(response.data.files);
      setError("");
    } catch (err) {
      setError("Failed to load files");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchFiles, 30000);

    return () => clearInterval(interval);
  }, [token, refreshTrigger]);

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const handleDownload = (file) => {
    // Open the backend download endpoint with token as query parameter
    // The backend will verify the token and redirect to the MinIO presigned URL
    const downloadUrl = `${API_BASE_URL}/api/files/${file.id}/download?token=${encodeURIComponent(token)}`;
    console.log('Opening download URL:', downloadUrl);
    console.log('Token:', token);
    window.open(downloadUrl, '_blank');
  };

  const handleDelete = async (file) => {
    if (!window.confirm(`Are you sure you want to delete "${file.original_filename}"?`)) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/api/files/${file.id}?token=${encodeURIComponent(token)}`);
      // Refresh the file list after deletion
      fetchFiles();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete file. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold mb-4">My Files</h2>
        <div className="text-center py-8 text-gray-500">Loading files...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">My Files</h2>
        <button
          onClick={fetchFiles}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {files.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No files uploaded yet. Upload your first file above!
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Filename
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Storage
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Uploaded
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {files.map((file) => (
                <tr key={file.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {file.original_filename}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">
                      {formatFileSize(file.file_size)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        file.storage_location === "minio"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {file.storage_location.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(file.uploaded_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => handleDownload(file)}
                      className="text-blue-600 hover:text-blue-900 mr-4"
                    >
                      View
                    </button>
                    <button
                      onClick={() => handleDelete(file)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 text-sm text-gray-500">
        Auto-refreshes every 30 seconds to show sync updates
      </div>
    </div>
  );
}
