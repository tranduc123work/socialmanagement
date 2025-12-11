'use client';

import { useState, useEffect, forwardRef, useImperativeHandle, useRef } from 'react';
import { RefreshCw, Trash2, Image as ImageIcon, Calendar, Loader2, Check, Square, CheckSquare, ChevronLeft, ChevronRight, X, Bot, Search, Download, Upload, Plus } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

// Dynamic API URL
const getApiUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return `http://${window.location.hostname}:8000`;
    }
    return `${window.location.protocol}//${window.location.host}`;
  }
  return 'http://localhost:8000';
};

interface FuguImage {
  id: number;
  url: string;
  name: string;
  size: number;
  createdAt: string;
}

interface UploadFile {
  file: File;
  preview: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
}

export interface FuguImageGalleryRef {
  refresh: () => void;
}

interface FuguImageGalleryProps {
  onRequestAgentEdit?: (message: string) => void;
}

export const FuguImageGallery = forwardRef<FuguImageGalleryRef, FuguImageGalleryProps>(
  ({ onRequestAgentEdit }, ref) => {
    const { tokens } = useAuth();
    const [images, setImages] = useState<FuguImage[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [selectedImageIds, setSelectedImageIds] = useState<number[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedImage, setSelectedImage] = useState<FuguImage | null>(null);
    const [showLightbox, setShowLightbox] = useState(false);
    const [lightboxIndex, setLightboxIndex] = useState(0);

    // Upload states
    const [showUpload, setShowUpload] = useState(false);
    const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const apiUrl = getApiUrl();

    // Fetch images on mount
    useEffect(() => {
      loadImages();
    }, [tokens]);

    const loadImages = async () => {
      if (!tokens) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const response = await fetch(`${apiUrl}/api/media/`, {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          // Show all images from media library
          const fuguImages: FuguImage[] = data
            .filter((item: any) => item.file_type === 'image')
            .map((item: any) => ({
              id: item.id,
              url: item.file_url,
              name: item.file_url.split('/').pop() || 'unknown',
              size: item.file_size,
              createdAt: item.created_at
            }))
            .sort((a: FuguImage, b: FuguImage) =>
              new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
            );
          setImages(fuguImages);
        }
      } catch (error) {
        console.error('Failed to load images:', error);
      } finally {
        setIsLoading(false);
      }
    };

    const handleRefresh = async () => {
      setIsRefreshing(true);
      await loadImages();
      setIsRefreshing(false);
    };

    // Expose refresh method to parent
    useImperativeHandle(ref, () => ({
      refresh: handleRefresh
    }));

    const handleDelete = async (imageId: number) => {
      if (!confirm('Bạn có chắc muốn xóa ảnh này?')) return;

      try {
        const response = await fetch(`${apiUrl}/api/media/${imageId}/`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${tokens?.access_token}`
          }
        });

        if (response.ok) {
          setImages(prev => prev.filter(img => img.id !== imageId));
          setSelectedImageIds(prev => prev.filter(id => id !== imageId));
          if (selectedImage?.id === imageId) {
            setSelectedImage(null);
          }
        } else {
          alert('Không thể xóa ảnh. Vui lòng thử lại.');
        }
      } catch (error) {
        console.error('Failed to delete image:', error);
        alert('Không thể xóa ảnh. Vui lòng thử lại.');
      }
    };

    const handleBulkDelete = async () => {
      if (selectedImageIds.length === 0) return;
      if (!confirm(`Bạn có chắc muốn xóa ${selectedImageIds.length} ảnh đã chọn?`)) return;

      let successCount = 0;
      for (const imageId of selectedImageIds) {
        try {
          const response = await fetch(`${apiUrl}/api/media/${imageId}/`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${tokens?.access_token}`
            }
          });
          if (response.ok) {
            successCount++;
          }
        } catch (error) {
          console.error(`Failed to delete image ${imageId}:`, error);
        }
      }

      if (successCount > 0) {
        setImages(prev => prev.filter(img => !selectedImageIds.includes(img.id)));
        setSelectedImageIds([]);
        alert(`Đã xóa ${successCount}/${selectedImageIds.length} ảnh.`);
      }
    };

    // Upload handlers
    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files) {
        addFilesToUpload(Array.from(files));
      }
    };

    const addFilesToUpload = (files: File[]) => {
      const imageFiles = files.filter(f => f.type.startsWith('image/'));
      const newUploadFiles: UploadFile[] = imageFiles.map(file => ({
        file,
        preview: URL.createObjectURL(file),
        progress: 0,
        status: 'pending'
      }));
      setUploadFiles(prev => [...prev, ...newUploadFiles]);
      setShowUpload(true);
    };

    const removeUploadFile = (index: number) => {
      setUploadFiles(prev => {
        const file = prev[index];
        if (file) {
          URL.revokeObjectURL(file.preview);
        }
        return prev.filter((_, i) => i !== index);
      });
    };

    const handleUpload = async () => {
      if (uploadFiles.length === 0 || !tokens) return;

      setIsUploading(true);
      let successCount = 0;

      // Get or create the AI Generated folder first
      let aiFolderId: number | null = null;
      try {
        const folderResponse = await fetch(`${apiUrl}/api/media/folders/ai-generated`, {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`
          }
        });
        if (folderResponse.ok) {
          const folderData = await folderResponse.json();
          aiFolderId = folderData.id;
        }
      } catch (error) {
        console.error('Failed to get AI folder:', error);
      }

      for (let i = 0; i < uploadFiles.length; i++) {
        const uploadFile = uploadFiles[i];
        if (uploadFile.status === 'success') continue;

        // Update status to uploading
        setUploadFiles(prev => prev.map((f, idx) =>
          idx === i ? { ...f, status: 'uploading' as const, progress: 0 } : f
        ));

        try {
          const formData = new FormData();
          formData.append('file', uploadFile.file);
          formData.append('file_type', 'image');
          // Add AI folder ID so images appear in Fugu gallery
          if (aiFolderId) {
            formData.append('folder_id', aiFolderId.toString());
          }

          const response = await fetch(`${apiUrl}/api/media/upload`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`
            },
            body: formData
          });

          if (response.ok) {
            successCount++;
            setUploadFiles(prev => prev.map((f, idx) =>
              idx === i ? { ...f, status: 'success' as const, progress: 100 } : f
            ));
          } else {
            setUploadFiles(prev => prev.map((f, idx) =>
              idx === i ? { ...f, status: 'error' as const } : f
            ));
          }
        } catch (error) {
          console.error(`Failed to upload ${uploadFile.file.name}:`, error);
          setUploadFiles(prev => prev.map((f, idx) =>
            idx === i ? { ...f, status: 'error' as const } : f
          ));
        }
      }

      setIsUploading(false);

      if (successCount > 0) {
        // Refresh image list
        await loadImages();
        // Clear successful uploads after delay
        setTimeout(() => {
          setUploadFiles(prev => prev.filter(f => f.status !== 'success'));
          if (uploadFiles.every(f => f.status === 'success')) {
            setShowUpload(false);
          }
        }, 1500);
      }
    };

    const cancelUpload = () => {
      uploadFiles.forEach(f => URL.revokeObjectURL(f.preview));
      setUploadFiles([]);
      setShowUpload(false);
    };

    // Drag & drop handlers
    const handleDragOver = (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      addFilesToUpload(files);
    };

    // Toggle image selection
    const toggleImageSelection = (imageId: number, e: React.MouseEvent) => {
      e.stopPropagation();
      setSelectedImageIds(prev =>
        prev.includes(imageId)
          ? prev.filter(id => id !== imageId)
          : [...prev, imageId]
      );
    };

    // Select all images
    const selectAllImages = () => {
      if (selectedImageIds.length === filteredImages.length) {
        setSelectedImageIds([]);
      } else {
        setSelectedImageIds(filteredImages.map(img => img.id));
      }
    };

    // Filter images by search
    const filteredImages = images.filter(img =>
      img.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Format file size
    const formatSize = (bytes: number) => {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
    };

    // Open lightbox
    const openLightbox = (image: FuguImage) => {
      const index = filteredImages.findIndex(img => img.id === image.id);
      setLightboxIndex(index >= 0 ? index : 0);
      setShowLightbox(true);
    };

    // Download image
    const downloadImage = async (image: FuguImage) => {
      try {
        const response = await fetch(`${apiUrl}${image.url}`);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = image.name;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error('Failed to download image:', error);
        alert('Không thể tải ảnh. Vui lòng thử lại.');
      }
    };

    const renderImageCard = (image: FuguImage) => {
      const isSelected = selectedImageIds.includes(image.id);

      return (
        <div
          key={image.id}
          onClick={() => {
            setSelectedImage(image);
          }}
          className={`bg-white rounded-lg border-2 overflow-hidden cursor-pointer hover:shadow-lg transition-all ${
            isSelected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200'
          }`}
        >
          {/* Image with checkbox overlay */}
          <div className="aspect-square bg-gray-100 relative group">
            <img
              src={`${apiUrl}${image.url}`}
              alt={image.name}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
                e.currentTarget.parentElement!.innerHTML = '<div class="w-full h-full flex items-center justify-center bg-gray-200"><svg class="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg></div>';
              }}
            />

            {/* Checkbox overlay - higher z-index to be clickable */}
            <button
              onClick={(e) => toggleImageSelection(image.id, e)}
              className={`absolute top-2 left-2 z-20 w-6 h-6 rounded flex items-center justify-center transition-all ${
                isSelected
                  ? 'bg-blue-500 text-white'
                  : 'bg-white/80 hover:bg-white text-gray-400 hover:text-gray-600 border border-gray-300'
              }`}
            >
              {isSelected ? <Check className="w-4 h-4" /> : <Square className="w-4 h-4" />}
            </button>

            {/* Zoom on hover - lower z-index */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                openLightbox(image);
              }}
              className="absolute inset-0 z-10 bg-black/0 hover:bg-black/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all"
            >
              <span className="bg-white/90 text-gray-700 px-3 py-1 rounded-full text-sm font-medium">
                Phóng to
              </span>
            </button>
          </div>

          {/* Info */}
          <div className="p-3">
            <p className="text-xs text-gray-500 truncate mb-1" title={image.name}>
              {image.name}
            </p>
            <div className="flex items-center justify-between text-xs text-gray-400">
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {new Date(image.createdAt).toLocaleDateString('vi-VN')}
              </div>
              <span>{formatSize(image.size)}</span>
            </div>
          </div>
        </div>
      );
    };

    return (
      <div className="h-full bg-gray-50 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Thư viện ảnh
              </h2>
              <p className="text-sm text-gray-500">
                {filteredImages.length} ảnh
                {selectedImageIds.length > 0 && (
                  <span className="ml-2 text-blue-600 font-medium">
                    • Đã chọn {selectedImageIds.length} ảnh
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* Select All Button */}
              {filteredImages.length > 0 && (
                <button
                  onClick={selectAllImages}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  {selectedImageIds.length === filteredImages.length ? (
                    <>
                      <CheckSquare className="w-4 h-4" />
                      Bỏ chọn
                    </>
                  ) : (
                    <>
                      <Square className="w-4 h-4" />
                      Chọn tất cả
                    </>
                  )}
                </button>
              )}

              {/* Batch Edit Button */}
              {selectedImageIds.length > 0 && (
                <button
                  onClick={() => {
                    const message = `Tôi muốn chỉnh sửa ${selectedImageIds.length} ảnh có ID: ${selectedImageIds.join(', ')}`;
                    if (onRequestAgentEdit) {
                      onRequestAgentEdit(message);
                    }
                  }}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                >
                  <Bot className="w-4 h-4" />
                  Nhờ Fugu chỉnh sửa ({selectedImageIds.length})
                </button>
              )}

              {/* Bulk Delete Button */}
              {selectedImageIds.length > 0 && (
                <button
                  onClick={handleBulkDelete}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Xóa ({selectedImageIds.length})
                </button>
              )}

              {/* Upload Button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Upload className="w-4 h-4" />
                Tải lên
              </button>

              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                Làm mới
              </button>

              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Tìm kiếm theo tên file..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>

          {/* Upload Panel - Inline */}
          {showUpload && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-700">
                  Tải lên ảnh ({uploadFiles.length} file)
                </h4>
                <button
                  onClick={cancelUpload}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* File previews */}
              {uploadFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {uploadFiles.map((file, index) => (
                    <div
                      key={index}
                      className={`relative w-16 h-16 rounded-lg overflow-hidden border-2 ${
                        file.status === 'success' ? 'border-green-500' :
                        file.status === 'error' ? 'border-red-500' :
                        file.status === 'uploading' ? 'border-blue-500' :
                        'border-gray-300'
                      }`}
                    >
                      <img
                        src={file.preview}
                        alt={file.file.name}
                        className="w-full h-full object-cover"
                      />
                      {file.status === 'uploading' && (
                        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                          <Loader2 className="w-5 h-5 text-white animate-spin" />
                        </div>
                      )}
                      {file.status === 'success' && (
                        <div className="absolute inset-0 bg-green-500/50 flex items-center justify-center">
                          <Check className="w-5 h-5 text-white" />
                        </div>
                      )}
                      {file.status === 'error' && (
                        <div className="absolute inset-0 bg-red-500/50 flex items-center justify-center">
                          <X className="w-5 h-5 text-white" />
                        </div>
                      )}
                      {file.status === 'pending' && (
                        <button
                          onClick={() => removeUploadFile(index)}
                          className="absolute top-0.5 right-0.5 w-4 h-4 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  ))}

                  {/* Add more button */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center text-gray-400 hover:border-blue-500 hover:text-blue-500 transition-colors"
                  >
                    <Plus className="w-6 h-6" />
                  </button>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={handleUpload}
                  disabled={isUploading || uploadFiles.length === 0 || uploadFiles.every(f => f.status === 'success')}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Đang tải...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Tải lên {uploadFiles.filter(f => f.status === 'pending').length} ảnh
                    </>
                  )}
                </button>
                <button
                  onClick={cancelUpload}
                  disabled={isUploading}
                  className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
                >
                  Hủy
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Images Grid with Drag & Drop */}
        <div
          className={`flex-1 overflow-y-auto p-6 transition-colors ${
            isDragging ? 'bg-blue-50' : ''
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : filteredImages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              {/* Drag & Drop Zone for empty state */}
              <div
                className={`w-full max-w-md p-8 rounded-xl border-2 border-dashed transition-colors ${
                  isDragging
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-300 hover:border-blue-400'
                }`}
              >
                <div className="w-16 h-16 mx-auto bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center mb-4">
                  <ImageIcon className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">
                  {searchQuery ? 'Không tìm thấy ảnh' : 'Chưa có ảnh nào'}
                </h3>
                <p className="text-gray-500 mb-4">
                  {searchQuery
                    ? 'Thử tìm kiếm với từ khóa khác.'
                    : 'Kéo thả ảnh vào đây hoặc nhấn nút bên dưới'
                  }
                </p>
                {!searchQuery && (
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <Upload className="w-4 h-4" />
                    Chọn ảnh để tải lên
                  </button>
                )}
              </div>
            </div>
          ) : (
            <>
              {/* Drag overlay indicator */}
              {isDragging && (
                <div className="fixed inset-0 z-30 bg-blue-500/10 pointer-events-none flex items-center justify-center">
                  <div className="bg-white p-6 rounded-xl shadow-lg border-2 border-blue-500 border-dashed">
                    <Upload className="w-12 h-12 text-blue-500 mx-auto mb-2" />
                    <p className="text-blue-600 font-medium">Thả ảnh vào đây</p>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {filteredImages.map(renderImageCard)}
              </div>
            </>
          )}
        </div>

        {/* Image Detail Slide-over */}
        {selectedImage && !showLightbox && (
          <>
            <div
              className="fixed inset-0 bg-black/30 z-40"
              onClick={() => setSelectedImage(null)}
            />
            <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800">Chi tiết ảnh</h3>
                <button
                  onClick={() => setSelectedImage(null)}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {/* Image Preview */}
                <div
                  className="rounded-lg overflow-hidden border border-gray-200 cursor-pointer hover:opacity-90"
                  onClick={() => openLightbox(selectedImage)}
                >
                  <img
                    src={`${apiUrl}${selectedImage.url}`}
                    alt={selectedImage.name}
                    className="w-full h-auto"
                  />
                  <p className="text-xs text-gray-500 text-center py-1 bg-gray-50">
                    Click để phóng to
                  </p>
                </div>

                {/* Info */}
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Tên file</label>
                    <p className="text-sm text-gray-600 break-all">{selectedImage.name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Kích thước</label>
                    <p className="text-sm text-gray-600">{formatSize(selectedImage.size)}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Ngày tạo</label>
                    <p className="text-sm text-gray-600">
                      {new Date(selectedImage.createdAt).toLocaleString('vi-VN')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="px-6 py-4 border-t border-gray-200 space-y-2">
                <button
                  onClick={() => downloadImage(selectedImage)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Tải xuống
                </button>
                <button
                  onClick={() => {
                    const message = `Tôi muốn chỉnh sửa ảnh có ID: ${selectedImage.id}`;
                    setSelectedImage(null);
                    if (onRequestAgentEdit) {
                      onRequestAgentEdit(message);
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
                >
                  <Bot className="w-4 h-4" />
                  Nhờ Fugu chỉnh sửa
                </button>
                <button
                  onClick={() => {
                    handleDelete(selectedImage.id);
                    setSelectedImage(null);
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Xóa ảnh
                </button>
              </div>
            </div>
          </>
        )}

        {/* Lightbox */}
        {showLightbox && filteredImages.length > 0 && (
          <div
            className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center"
            onClick={() => setShowLightbox(false)}
          >
            {/* Close button */}
            <button
              onClick={() => setShowLightbox(false)}
              className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors z-10"
            >
              <X className="w-6 h-6" />
            </button>

            {/* Image counter */}
            {filteredImages.length > 1 && (
              <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1 rounded-full text-sm">
                {lightboxIndex + 1} / {filteredImages.length}
              </div>
            )}

            {/* Previous button */}
            {filteredImages.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setLightboxIndex((prev) => (prev - 1 + filteredImages.length) % filteredImages.length);
                }}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
              >
                <ChevronLeft className="w-8 h-8" />
              </button>
            )}

            {/* Main image */}
            <img
              src={`${apiUrl}${filteredImages[lightboxIndex]?.url}`}
              alt={filteredImages[lightboxIndex]?.name}
              className="max-w-[90vw] max-h-[85vh] object-contain rounded-lg shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            />

            {/* Next button */}
            {filteredImages.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setLightboxIndex((prev) => (prev + 1) % filteredImages.length);
                }}
                className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
              >
                <ChevronRight className="w-8 h-8" />
              </button>
            )}

            {/* Thumbnail strip */}
            {filteredImages.length > 1 && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 bg-black/50 p-2 rounded-lg max-w-[80vw] overflow-x-auto">
                {filteredImages.slice(0, 10).map((img, idx) => (
                  <button
                    key={img.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setLightboxIndex(idx);
                    }}
                    className={`flex-shrink-0 w-12 h-12 rounded overflow-hidden border-2 transition-all ${
                      idx === lightboxIndex
                        ? 'border-white scale-110'
                        : 'border-transparent opacity-60 hover:opacity-100'
                    }`}
                  >
                    <img
                      src={`${apiUrl}${img.url}`}
                      alt={`Thumb ${idx + 1}`}
                      className="w-full h-full object-cover"
                    />
                  </button>
                ))}
                {filteredImages.length > 10 && (
                  <div className="flex-shrink-0 w-12 h-12 rounded bg-white/20 flex items-center justify-center text-white text-xs">
                    +{filteredImages.length - 10}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);

FuguImageGallery.displayName = 'FuguImageGallery';
