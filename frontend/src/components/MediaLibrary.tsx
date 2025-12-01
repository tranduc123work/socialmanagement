'use client';

import { useState, useRef, useEffect } from 'react';
import { Upload, Folder, Search, Sparkles, Video, Grid3x3, List, Trash2, ImagePlus } from 'lucide-react';
import { ImageWithFallback } from './figma/ImageWithFallback';
import { useAuth } from '@/contexts/AuthContext';
import { useTasks } from '@/contexts/TaskContext';
import { AITaskService } from '@/services/aiTaskService';
import { toast } from 'sonner';

// Dynamic API URL - uses same hostname as frontend but port 8000
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    return `http://${hostname}:8000`;
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

interface MediaItem {
  id: string;
  type: 'image' | 'video';
  url: string;
  name: string;
  folder: string;
  tags: string[];
  size: string;
  uploadDate: Date;
}

// Mock media removed - using real API data only

const folders = ['Tất cả', 'Sản phẩm', 'Marketing', 'Video', 'AI Generated'];

export function MediaLibrary() {
  const { tokens } = useAuth();
  const { tasks, addTask } = useTasks();

  const [selectedFolder, setSelectedFolder] = useState('Tất cả');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMedia, setSelectedMedia] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showUpload, setShowUpload] = useState(false);

  // Upload states
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadFolder, setUploadFolder] = useState('Sản phẩm');
  const [uploadTags, setUploadTags] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  // AI Image Generator states
  const [aiPrompt, setAiPrompt] = useState('');
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);
  const [aiReferenceImages, setAiReferenceImages] = useState<{url: string; file: File}[]>([]);
  const [aiImageSize, setAiImageSize] = useState('1080x1080');
  const [aiCreativity, setAiCreativity] = useState('medium');
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [aiImageCount, setAiImageCount] = useState(1);  // Số lượng ảnh cần tạo
  const [aiGeneratePerRef, setAiGeneratePerRef] = useState(false);  // Tạo 1 ảnh cho mỗi ảnh tham chiếu
  const [aiGenerationProgress, setAiGenerationProgress] = useState({ current: 0, total: 0 });  // Tiến trình

  // State for media from API
  const [apiMedia, setApiMedia] = useState<MediaItem[]>([]);
  const [isLoadingMedia, setIsLoadingMedia] = useState(true);

  const aiImageInputRef = useRef<HTMLInputElement>(null);

  // API base URL
  const API_BASE_URL = getApiUrl();

  // Restore AI form state from localStorage on mount
  useEffect(() => {
    const savedState = localStorage.getItem('ai_image_generator_state');
    if (savedState) {
      try {
        const state = JSON.parse(savedState);
        if (state.aiPrompt) setAiPrompt(state.aiPrompt);
        if (state.aiImageSize) setAiImageSize(state.aiImageSize);
        if (state.aiCreativity) setAiCreativity(state.aiCreativity);
        if (state.aiImageCount) setAiImageCount(state.aiImageCount);
        if (state.aiGeneratePerRef !== undefined) setAiGeneratePerRef(state.aiGeneratePerRef);

        // Restore reference images from base64
        if (state.aiReferenceImages && state.aiReferenceImages.length > 0) {
          const restoreImages = async () => {
            const restoredImages = await Promise.all(
              state.aiReferenceImages.map(async (img: { url: string; name: string }) => {
                try {
                  const response = await fetch(img.url);
                  const blob = await response.blob();
                  const file = new File([blob], img.name, { type: blob.type });
                  return { url: img.url, file };
                } catch (error) {
                  console.error('Error restoring image:', error);
                  return null;
                }
              })
            );
            setAiReferenceImages(restoredImages.filter(img => img !== null) as {url: string; file: File}[]);
          };
          restoreImages();
        }
      } catch (error) {
        console.error('Error restoring AI state:', error);
      }
    }
  }, []);

  // Save AI form state to localStorage whenever it changes
  useEffect(() => {
    const saveState = async () => {
      try {
        // Convert reference images to base64 for storage
        const referenceImagesData = await Promise.all(
          aiReferenceImages.map(async (img) => {
            return {
              url: img.url,
              name: img.file.name
            };
          })
        );

        const state = {
          aiPrompt,
          aiImageSize,
          aiCreativity,
          aiImageCount,
          aiGeneratePerRef,
          aiReferenceImages: referenceImagesData,
          savedAt: new Date().toISOString()
        };
        localStorage.setItem('ai_image_generator_state', JSON.stringify(state));
      } catch (error) {
        console.error('Error saving AI state:', error);
      }
    };

    // Debounce save to avoid too many writes
    const timeoutId = setTimeout(saveState, 500);
    return () => clearTimeout(timeoutId);
  }, [aiPrompt, aiImageSize, aiCreativity, aiImageCount, aiGeneratePerRef, aiReferenceImages]);

  // Fetch media from API on mount and when tokens change
  useEffect(() => {
    fetchMediaFromAPI();
  }, [tokens]);

  // Monitor task completion and auto-refresh media
  useEffect(() => {
    // Check if any image generation tasks just completed
    const imageTasks = Array.from(tasks.values()).filter(
      task => task.task_type === 'image' && task.status === 'completed'
    );

    if (imageTasks.length > 0) {
      // Refresh media list when image generation completes
      fetchMediaFromAPI();
    }
  }, [tasks]);

  // Check active image generation tasks to show loading state
  const activeImageTasks = Array.from(tasks.values()).filter(
    task => task.task_type === 'image' && (task.status === 'pending' || task.status === 'processing')
  );
  const hasActiveImageGeneration = activeImageTasks.length > 0;

  const fetchMediaFromAPI = async () => {
    if (!tokens) {
      setIsLoadingMedia(false);
      return;
    }

    setIsLoadingMedia(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/media/`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        const mediaItems: MediaItem[] = data.map((item: {
          id: number;
          file_url: string;
          file_type: string;
          file_size: number;
          folder_name?: string;
          created_at: string;
        }) => ({
          id: `api-${item.id}`,
          type: item.file_type as 'image' | 'video',
          url: `${API_BASE_URL}${item.file_url}`,
          name: item.file_url.split('/').pop() || 'unknown',
          folder: item.folder_name || 'Chưa phân loại',
          tags: item.folder_name === 'AI Generated' ? ['ai', 'generated'] : [],
          size: `${(item.file_size / 1024 / 1024).toFixed(2)} MB`,
          uploadDate: new Date(item.created_at),
        }));
        setApiMedia(mediaItems);
      }
    } catch (error) {
      console.error('Error fetching media:', error);
    } finally {
      setIsLoadingMedia(false);
    }
  };

  // Use API media only (no mock data)
  const allMedia = apiMedia;

  const filteredMedia = allMedia.filter((item: MediaItem) => {
    const matchesFolder = selectedFolder === 'Tất cả' || item.folder === selectedFolder;
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesFolder && matchesSearch;
  });

  const toggleSelection = (id: string) => {
    setSelectedMedia((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  // AI Image Generator with async task system
  const handleGenerateAIImage = async () => {
    if (!aiPrompt.trim()) {
      toast.error('Vui lòng nhập prompt mô tả ảnh');
      return;
    }

    try {
      // Submit task to async service
      const response = await AITaskService.submitImageTask(tokens!.access_token, {
        prompt: aiPrompt,
        size: aiImageSize,
        creativity: aiCreativity,
        reference_images: aiReferenceImages.map(img => img.file)
      });

      // Add task to tracker
      addTask(response.task_id, 'image');

      // Clear form and notify user
      toast.success('Đã bắt đầu tạo ảnh AI', {
        description: 'Bạn có thể tiếp tục làm việc. Sẽ có thông báo khi hoàn thành.'
      });

      // Clear form (but keep it in localStorage if user wants to generate more)
      setGeneratedImage(null);

    } catch (error) {
      console.error('Error submitting image task:', error);
      toast.error('Lỗi khi gửi yêu cầu tạo ảnh', {
        description: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  };

  const handleAIImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      const newImages = Array.from(files).map(file => ({
        url: URL.createObjectURL(file),
        file: file
      }));
      setAiReferenceImages(prev => [...prev, ...newImages]);
    }
  };

  const removeAIReferenceImage = (imgUrl: string) => {
    setAiReferenceImages(prev => {
      // Revoke object URL to prevent memory leak
      const imgToRemove = prev.find(img => img.url === imgUrl);
      if (imgToRemove) {
        URL.revokeObjectURL(imgToRemove.url);
      }
      return prev.filter(img => img.url !== imgUrl);
    });
  };

  // Delete media handler
  const handleDeleteMedia = async (mediaId: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa ảnh này?')) {
      return;
    }

    if (!tokens) {
      alert('Vui lòng đăng nhập để xóa file');
      return;
    }

    try {
      // Extract numeric ID from "api-{id}" format
      const numericId = mediaId.replace('api-', '');

      const response = await fetch(`${API_BASE_URL}/api/media/${numericId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (response.ok) {
        alert('Đã xóa thành công!');
        // Refresh media list
        await fetchMediaFromAPI();
      } else {
        alert('Không thể xóa file. Vui lòng thử lại.');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert(`Có lỗi xảy ra khi xóa: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Add media to AI reference images
  const handleAddToAIReference = async (mediaUrl: string, mediaName: string) => {
    try {
      // Fetch the image
      const response = await fetch(mediaUrl);
      const blob = await response.blob();

      // Convert blob to File
      const file = new File([blob], mediaName, { type: blob.type });

      // Add to reference images
      const objectUrl = URL.createObjectURL(blob);
      setAiReferenceImages(prev => [...prev, { url: objectUrl, file: file }]);

      alert('Đã thêm ảnh vào phần tham khảo AI!');
    } catch (error) {
      console.error('Error adding to AI reference:', error);
      alert('Không thể thêm ảnh. Vui lòng thử lại.');
    }
  };

  // Upload handlers
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      setUploadFiles(Array.from(files));
    }
  };

  const handleUpload = async () => {
    if (uploadFiles.length === 0) {
      alert('Vui lòng chọn file để tải lên');
      return;
    }

    if (!tokens) {
      alert('Vui lòng đăng nhập để tải file lên');
      return;
    }

    setIsUploading(true);

    try {
      let successCount = 0;
      let failCount = 0;

      for (const file of uploadFiles) {
        try {
          const formData = new FormData();
          formData.append('file', file);

          // Determine file type
          const fileType = file.type.startsWith('image/') ? 'image' : 'video';
          formData.append('file_type', fileType);

          const response = await fetch(`${API_BASE_URL}/api/media/upload`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`
            },
            body: formData,
          });

          if (response.ok) {
            successCount++;
          } else {
            failCount++;
            console.error(`Failed to upload ${file.name}`);
          }
        } catch (error) {
          failCount++;
          console.error(`Error uploading ${file.name}:`, error);
        }
      }

      // Refresh media list
      await fetchMediaFromAPI();

      // Show result
      if (failCount === 0) {
        alert(`Đã tải lên thành công ${successCount} file!`);
      } else {
        alert(`Hoàn thành: ${successCount} thành công, ${failCount} thất bại`);
      }

      // Reset upload state
      setUploadFiles([]);
      setUploadTags('');
      setShowUpload(false);
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Có lỗi xảy ra khi tải file lên: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-gray-900 mb-2">Thư viện Media</h2>
        <p className="text-gray-600">Quản lý hình ảnh và video</p>
      </div>

      {/* Toolbar */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => setShowUpload(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Tải lên
            </button>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg ${
                viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
              }`}
            >
              <Grid3x3 className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg ${
                viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
              }`}
            >
              <List className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="mt-4 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm theo tên hoặc tag..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* AI Image Generator Section */}
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border-2 border-purple-200 p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-6 h-6 text-purple-600" />
          <h3 className="text-gray-900">AI Image Generator</h3>
        </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left column: Prompt and Settings */}
            <div className="space-y-4">
              {/* Prompt Input */}
              <div>
                <label className="block text-sm text-gray-700 mb-2">
                  Mô tả ảnh (prompt) <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  placeholder="Ví dụ: Hình ảnh sản phẩm đồng hồ cao cấp trên nền trắng, ánh sáng studio chuyên nghiệp, chụp cận cảnh, chất lượng cao, phong cách tối giản hiện đại"
                  className="w-full h-32 p-4 border-2 border-purple-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* AI Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-700 mb-2">Kích thước</label>
                  <select
                    value={aiImageSize}
                    onChange={(e) => setAiImageSize(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="1080x1080">1080x1080 (Square)</option>
                    <option value="1200x628">1200x628 (Banner)</option>
                    <option value="1080x1920">1080x1920 (Story)</option>
                    <option value="1920x1080">1920x1080 (Landscape)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-700 mb-2">Độ sáng tạo</label>
                  <select
                    value={aiCreativity}
                    onChange={(e) => setAiCreativity(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="low">Thấp (Realistic)</option>
                    <option value="medium">Trung bình</option>
                    <option value="high">Cao (Creative)</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleGenerateAIImage}
                disabled={!aiPrompt.trim()}
                className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
              >
                {hasActiveImageGeneration ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Đang tạo {activeImageTasks.length} ảnh...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Tạo ảnh với AI
                  </>
                )}
              </button>

              {hasActiveImageGeneration && (
                <p className="text-xs text-blue-600 mt-2 text-center">
                  💡 Bạn có thể chuyển sang tab khác trong khi AI đang tạo ảnh
                </p>
              )}
            </div>

            {/* Right column: Reference Images */}
            <div>
              <label className="block text-sm text-gray-700 mb-2">
                Ảnh tham khảo (Reference Images)
              </label>
              <p className="text-xs text-gray-500 mb-3">
                Upload ảnh để AI tham khảo phong cách, bố cục hoặc nội dung
              </p>

              {/* Display uploaded reference images */}
              {aiReferenceImages.length > 0 && (
                <div className="grid grid-cols-3 gap-3 mb-3">
                  {aiReferenceImages.map((img, index) => (
                    <div key={index} className="relative aspect-square group">
                      <ImageWithFallback
                        src={img.url}
                        alt={`Reference ${index + 1}`}
                        className="w-full h-full object-cover rounded-lg border-2 border-purple-200"
                      />
                      <button
                        onClick={() => removeAIReferenceImage(img.url)}
                        className="absolute top-2 right-2 w-6 h-6 bg-red-500 text-white rounded-full hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-sm"
                      >
                        ×
                      </button>
                      <div className="absolute bottom-2 left-2 px-2 py-1 bg-black bg-opacity-70 text-white text-xs rounded">
                        #{index + 1}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Display generated image */}
              {generatedImage && (
                <div className="mb-3">
                  <p className="text-sm text-gray-700 mb-2">✨ Ảnh vừa tạo:</p>
                  <div className="relative aspect-square max-w-xs">
                    <ImageWithFallback
                      src={generatedImage}
                      alt="AI Generated"
                      className="w-full h-full object-cover rounded-lg border-2 border-green-400"
                    />
                    <div className="absolute bottom-2 left-2 px-2 py-1 bg-green-500 text-white text-xs rounded">
                      AI Generated
                    </div>
                  </div>
                </div>
              )}

              {/* Upload button */}
              <div className="border-2 border-dashed border-purple-300 rounded-lg p-8 hover:border-purple-400 hover:bg-white transition-colors">
                <input
                  ref={aiImageInputRef}
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleAIImageUpload}
                  className="hidden"
                />
                <button
                  onClick={() => aiImageInputRef.current?.click()}
                  className="w-full flex flex-col items-center"
                >
                  <Upload className="w-10 h-10 text-purple-400 mb-2" />
                  <span className="text-sm text-gray-700">
                    Click để chọn ảnh tham khảo
                  </span>
                  <span className="text-xs text-gray-500 mt-1">
                    Có thể chọn nhiều ảnh
                  </span>
                </button>
              </div>

            {/* Tips */}
            <div className="mt-3 bg-white border border-purple-200 rounded-lg p-3">
              <p className="text-xs text-purple-900 mb-1">💡 Tips:</p>
              <ul className="text-xs text-purple-800 space-y-0.5">
                <li>• Mô tả chi tiết màu sắc, ánh sáng</li>
                <li>• Upload ảnh tham khảo phong cách</li>
                <li>• Dùng từ: "professional", "detailed"</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Folders sidebar */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 h-fit">
          <h3 className="text-gray-900 mb-4 flex items-center gap-2">
            <Folder className="w-5 h-5" />
            Thư mục
          </h3>
          <div className="space-y-1">
            {folders.map((folder) => (
              <button
                key={folder}
                onClick={() => setSelectedFolder(folder)}
                className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                  selectedFolder === folder
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                {folder}
              </button>
            ))}
          </div>
        </div>

        {/* Media grid/list */}
        <div className="lg:col-span-3">
          {selectedMedia.length > 0 && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg flex justify-between items-center">
              <span className="text-blue-900">
                Đã chọn {selectedMedia.length} file(s)
              </span>
              <button
                onClick={() => setSelectedMedia([])}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Bỏ chọn
              </button>
            </div>
          )}

          {viewMode === 'grid' ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredMedia.map((item) => (
                <div
                  key={item.id}
                  className={`bg-white rounded-lg border-2 hover:shadow-lg transition-all group ${
                    selectedMedia.includes(item.id)
                      ? 'border-blue-500 shadow-md'
                      : 'border-gray-200'
                  }`}
                >
                  <div
                    className="aspect-square relative overflow-hidden rounded-t-lg cursor-pointer"
                    onClick={() => toggleSelection(item.id)}
                  >
                    <ImageWithFallback
                      src={item.url}
                      alt={item.name}
                      className="w-full h-full object-cover"
                    />
                    {item.type === 'video' && (
                      <div className="absolute inset-0 bg-black bg-opacity-30 flex items-center justify-center">
                        <Video className="w-8 h-8 text-white" />
                      </div>
                    )}
                    {selectedMedia.includes(item.id) && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center">
                        ✓
                      </div>
                    )}

                    {/* Action buttons - show on hover */}
                    {item.type === 'image' && (
                      <div className="absolute bottom-2 left-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddToAIReference(item.url, item.name);
                          }}
                          className="flex-1 px-2 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs flex items-center justify-center gap-1"
                          title="Thêm vào AI Reference"
                        >
                          <ImagePlus className="w-3 h-3" />
                          AI Ref
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteMedia(item.id);
                          }}
                          className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs flex items-center justify-center"
                          title="Xóa ảnh"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="p-3">
                    <p className="text-sm text-gray-900 truncate mb-1">{item.name}</p>
                    <p className="text-xs text-gray-500">{item.size}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {item.tags.slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm text-gray-600">Tên</th>
                    <th className="px-6 py-3 text-left text-sm text-gray-600">Loại</th>
                    <th className="px-6 py-3 text-left text-sm text-gray-600">Thư mục</th>
                    <th className="px-6 py-3 text-left text-sm text-gray-600">Kích thước</th>
                    <th className="px-6 py-3 text-left text-sm text-gray-600">Tags</th>
                    <th className="px-6 py-3 text-left text-sm text-gray-600">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredMedia.map((item) => (
                    <tr
                      key={item.id}
                      className={`hover:bg-gray-50 ${
                        selectedMedia.includes(item.id) ? 'bg-blue-50' : ''
                      }`}
                    >
                      <td
                        className="px-6 py-4 cursor-pointer"
                        onClick={() => toggleSelection(item.id)}
                      >
                        <div className="flex items-center gap-3">
                          <ImageWithFallback
                            src={item.url}
                            alt={item.name}
                            className="w-10 h-10 rounded object-cover"
                          />
                          <span className="text-sm text-gray-900">{item.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-700 capitalize">{item.type}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-700">{item.folder}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-700">{item.size}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {item.tags.map((tag) => (
                            <span
                              key={tag}
                              className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          {item.type === 'image' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAddToAIReference(item.url, item.name);
                              }}
                              className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs flex items-center gap-1"
                              title="Thêm vào AI Reference"
                            >
                              <ImagePlus className="w-3 h-3" />
                              AI Ref
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteMedia(item.id);
                            }}
                            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs flex items-center gap-1"
                            title="Xóa"
                          >
                            <Trash2 className="w-3 h-3" />
                            Xóa
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-gray-900">Tải file lên</h3>
              <button
                onClick={() => setShowUpload(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <label className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
              <Upload className="w-12 h-12 text-gray-400 mb-4" />
              <span className="text-gray-600 mb-2">
                {uploadFiles.length > 0
                  ? `Đã chọn ${uploadFiles.length} file`
                  : 'Kéo thả file vào đây'}
              </span>
              <span className="text-sm text-gray-500">hoặc click để chọn file</span>
              <input
                type="file"
                multiple
                accept="image/*,video/*"
                className="hidden"
                onChange={handleFileSelect}
              />
            </label>

            {uploadFiles.length > 0 && (
              <div className="mt-4">
                <p className="text-sm text-gray-700 mb-2">File đã chọn:</p>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {uploadFiles.map((file, index) => (
                    <div key={index} className="text-xs text-gray-600 bg-gray-50 px-3 py-1 rounded">
                      {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-6">
              <label className="block text-sm text-gray-700 mb-2">Thư mục</label>
              <select
                value={uploadFolder}
                onChange={(e) => setUploadFolder(e.target.value)}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {folders.filter(f => f !== 'Tất cả').map((folder) => (
                  <option key={folder} value={folder}>{folder}</option>
                ))}
              </select>
            </div>

            <div className="mt-4">
              <label className="block text-sm text-gray-700 mb-2">Tags (phân cách bằng dấu phẩy)</label>
              <input
                type="text"
                value={uploadTags}
                onChange={(e) => setUploadTags(e.target.value)}
                placeholder="product, sale, summer"
                className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mt-6 flex gap-2">
              <button
                onClick={handleUpload}
                disabled={isUploading || uploadFiles.length === 0}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isUploading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Đang tải lên...
                  </>
                ) : (
                  'Tải lên'
                )}
              </button>
              <button
                onClick={() => {
                  setShowUpload(false);
                  setUploadFiles([]);
                  setUploadTags('');
                }}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                disabled={isUploading}
              >
                Hủy
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
