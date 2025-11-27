'use client';

import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  Image as ImageIcon,
  Video,
  Link2,
  Sparkles,
  Hash,
  Send,
  Save,
  Smile,
  Bold,
  Italic,
  Type,
  Upload,
  X,
  Crop,
  Maximize2,
  MapPin,
  MessageSquare,
  Pin,
  Clock,
  Settings,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { ImageWithFallback } from './figma/ImageWithFallback';

// Dynamic API URL - uses same hostname as frontend but port 8000
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    return `http://${hostname}:8000`;
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

type PostType = 'text' | 'photo' | 'video' | 'carousel' | 'link';

interface MediaFile {
  id: string;
  url: string;
  type: 'image' | 'video';
  file?: File;
}

interface LinkPreview {
  url: string;
  title: string;
  description: string;
  image: string;
}

export function PostComposer() {
  const [content, setContent] = useState('');
  const [postType, setPostType] = useState<PostType>('text');
  const [selectedPages, setSelectedPages] = useState<string[]>([]);
  const [media, setMedia] = useState<MediaFile[]>([]);
  const [linkPreview, setLinkPreview] = useState<LinkPreview | null>(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  
  // Advanced settings
  const [intervalPosting, setIntervalPosting] = useState(false);
  const [intervalMinutes, setIntervalMinutes] = useState(30);
  const [utmParams, setUtmParams] = useState({ source: '', medium: '', campaign: '' });
  const [location, setLocation] = useState('');
  const [firstComment, setFirstComment] = useState('');
  const [pinPost, setPinPost] = useState(false);

  // AI Content Generator
  const [aiPrompt, setAiPrompt] = useState('');
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const [isLoadingRewrite, setIsLoadingRewrite] = useState(false);
  const [aiTone, setAiTone] = useState<'professional' | 'casual' | 'funny' | 'formal'>('professional');

  // Publishing
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishStatus, setPublishStatus] = useState<{type: 'success' | 'error' | null, message: string}>({type: null, message: ''});

  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch real pages from API
  const { tokens } = useAuth();
  const [pages, setPages] = useState<Array<{id: string, name: string, avatar: string}>>([]);
  const [loadingPages, setLoadingPages] = useState(true);
  const [selectedPlatform, setSelectedPlatform] = useState<'facebook' | 'instagram'>('facebook');

  useEffect(() => {
    const fetchPages = async () => {
      if (!tokens) return;

      setLoadingPages(true);
      try {
        const response = await fetch(`${getApiUrl()}/api/platforms/accounts?platform=${selectedPlatform}`, {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          // Map API data to component format
          setPages(data.map((account: any) => ({
            id: account.id.toString(),
            name: account.name,
            avatar: account.profile_picture_url || 'https://via.placeholder.com/100'
          })));
        }
      } catch (error) {
        console.error('Error fetching pages:', error);
      } finally {
        setLoadingPages(false);
      }
    };

    fetchPages();
  }, [tokens, selectedPlatform]);

  // Publish post handler
  const handlePublish = async () => {
    if (!tokens || selectedPages.length === 0 || !content.trim()) {
      setPublishStatus({type: 'error', message: 'Vui lòng nhập nội dung và chọn ít nhất 1 page'});
      return;
    }

    setIsPublishing(true);
    setPublishStatus({type: null, message: ''});

    try {
      // Step 1: Create post
      const createResponse = await fetch(`${getApiUrl()}/api/platforms/posts`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: content,
          title: '',
          media_urls: media.map(m => m.url),
          media_type: postType === 'photo' && media.length > 1 ? 'carousel' : postType === 'photo' ? 'image' : postType === 'video' ? 'video' : 'none',
          link_url: linkPreview?.url || null,
          target_account_ids: selectedPages.map(id => parseInt(id)),
          scheduled_at: null
        })
      });

      if (!createResponse.ok) {
        const error = await createResponse.json();
        throw new Error(error.message || 'Tạo bài đăng thất bại');
      }

      const post = await createResponse.json();

      // Step 2: Publish post
      const publishResponse = await fetch(`${getApiUrl()}/api/platforms/posts/${post.id}/publish`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!publishResponse.ok) {
        const error = await publishResponse.json();
        throw new Error(error.message || 'Đăng bài thất bại');
      }

      const result = await publishResponse.json();

      if (result.success) {
        setPublishStatus({
          type: 'success',
          message: `Đã đăng thành công lên ${result.success_count}/${result.total} page(s)!`
        });
        // Clear form after successful publish
        setContent('');
        setMedia([]);
        setLinkPreview(null);
        setSelectedPages([]);
      } else {
        setPublishStatus({
          type: 'error',
          message: `Đăng bài thất bại: ${result.fail_count}/${result.total} page(s) lỗi`
        });
      }
    } catch (error) {
      console.error('Publish error:', error);
      setPublishStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Đã xảy ra lỗi khi đăng bài'
      });
    } finally {
      setIsPublishing(false);
    }
  };

  const emojis = ['😀', '😂', '❤️', '🔥', '👍', '🎉', '✨', '💯', '🚀', '💪', '👏', '🙌', '💰', '🎯', '⭐', '🌟'];

  const hashtagSuggestions = [
    '#trending', '#viral', '#facebook', '#business', '#marketing',
    '#sale', '#discount', '#newproduct', '#vietnam', '#hanoi'
  ];

  const aiSuggestions = [
    '🚀 Tối ưu cho viral: Thêm câu hỏi tương tác ở cuối bài',
    '💡 Gợi ý: Thêm call-to-action rõ ràng',
    '⭐ Tip: Đăng bài vào 18h-21h để tăng reach',
  ];

  const postTypes = [
    { id: 'text' as PostType, label: 'Bài viết text', icon: Type, description: 'Chỉ có nội dung văn bản' },
    { id: 'photo' as PostType, label: 'Bài viết ảnh', icon: ImageIcon, description: '1 hoặc nhiều ảnh' },
    { id: 'video' as PostType, label: 'Bài viết video', icon: Video, description: 'Upload video' },
    { id: 'carousel' as PostType, label: 'Carousel', icon: ImageIcon, description: 'Album nhiều ảnh' },
    { id: 'link' as PostType, label: 'Chia sẻ link', icon: Link2, description: 'Chia sẻ URL với preview' },
  ];

  // Text formatting functions
  const insertFormatting = (format: 'bold' | 'italic') => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = content.substring(start, end);
    
    let formattedText = '';
    if (format === 'bold') {
      formattedText = `**${selectedText}**`;
    } else if (format === 'italic') {
      formattedText = `*${selectedText}*`;
    }

    const newContent = content.substring(0, start) + formattedText + content.substring(end);
    setContent(newContent);
  };

  const insertEmoji = (emoji: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const newContent = content.substring(0, start) + emoji + content.substring(start);
    setContent(newContent);
    setShowEmojiPicker(false);
  };

  const insertHashtag = (hashtag: string) => {
    setContent(content + ' ' + hashtag);
  };

  const handleAIRewrite = async () => {
    if (!content.trim()) {
      alert('Vui lòng nhập nội dung trước khi viết lại với AI');
      return;
    }

    setIsLoadingRewrite(true);

    try {
      const formData = new FormData();
      formData.append('content', content);
      formData.append('style', 'improve');
      formData.append('language', 'vi');

      const response = await fetch(`${getApiUrl()}/api/ai/rewrite-test`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to rewrite content');
      }

      const data = await response.json();
      setContent(data.content);
    } catch (error) {
      console.error('AI rewrite error:', error);
      alert('Có lỗi xảy ra khi viết lại nội dung với AI');
    } finally {
      setIsLoadingRewrite(false);
    }
  };

  const handleAIGenerate = async () => {
    if (!aiPrompt.trim()) return;

    setIsLoadingAI(true);

    try {
      const formData = new FormData();
      formData.append('prompt', aiPrompt);
      formData.append('tone', aiTone);
      formData.append('include_hashtags', 'true');
      formData.append('include_emoji', 'true');
      formData.append('language', 'vi');

      const response = await fetch(`${getApiUrl()}/api/ai/generate-test`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to generate content');
      }

      const data = await response.json();
      setContent(data.content);
      setAiPrompt('');
    } catch (error) {
      console.error('AI generation error:', error);
      alert('Có lỗi xảy ra khi tạo nội dung với AI');
    } finally {
      setIsLoadingAI(false);
    }
  };

  // Upload file to server and get URL
  const uploadFileToServer = async (file: File): Promise<string> => {
    if (!tokens) {
      throw new Error('Not authenticated');
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', file.type.startsWith('video/') ? 'video' : 'image');

    const response = await fetch(`${getApiUrl()}/api/media/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${tokens.access_token}`
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Upload failed');
    }

    const result = await response.json();
    return result.file_url;
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !tokens) return;

    setPublishStatus({type: null, message: 'Đang upload ảnh...'});

    try {
      const uploadedMedia: MediaFile[] = [];

      for (const file of Array.from(files)) {
        // Upload to server
        const serverUrl = await uploadFileToServer(file);

        uploadedMedia.push({
          id: Math.random().toString(36),
          url: serverUrl, // Use server URL instead of blob URL
          type: 'image',
          file
        });
      }

      setMedia([...media, ...uploadedMedia]);
      if (postType === 'text') {
        setPostType(uploadedMedia.length > 1 ? 'carousel' : 'photo');
      }
      setPublishStatus({type: null, message: ''});
    } catch (error) {
      console.error('Upload error:', error);
      setPublishStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Upload ảnh thất bại'
      });
    }
  };

  const handleVideoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !tokens) return;

    setPublishStatus({type: null, message: 'Đang upload video...'});

    try {
      // Upload to server
      const serverUrl = await uploadFileToServer(file);

      const newMedia: MediaFile = {
        id: Math.random().toString(36),
        url: serverUrl, // Use server URL instead of blob URL
        type: 'video',
        file
      };
      setMedia([newMedia]);
      setPostType('video');
      setPublishStatus({type: null, message: ''});
    } catch (error) {
      console.error('Upload error:', error);
      setPublishStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Upload video thất bại'
      });
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);

    if (!tokens) return;

    const files = Array.from(e.dataTransfer.files);
    const imageFiles = files.filter(f => f.type.startsWith('image/'));
    const videoFiles = files.filter(f => f.type.startsWith('video/'));

    if (videoFiles.length > 0) {
      setPublishStatus({type: null, message: 'Đang upload video...'});
      try {
        const file = videoFiles[0];
        const serverUrl = await uploadFileToServer(file);
        setMedia([{
          id: Math.random().toString(36),
          url: serverUrl,
          type: 'video',
          file
        }]);
        setPostType('video');
        setPublishStatus({type: null, message: ''});
      } catch (error) {
        console.error('Upload error:', error);
        setPublishStatus({
          type: 'error',
          message: error instanceof Error ? error.message : 'Upload video thất bại'
        });
      }
    } else if (imageFiles.length > 0) {
      setPublishStatus({type: null, message: 'Đang upload ảnh...'});
      try {
        const uploadedMedia: MediaFile[] = [];
        for (const file of imageFiles) {
          const serverUrl = await uploadFileToServer(file);
          uploadedMedia.push({
            id: Math.random().toString(36),
            url: serverUrl,
            type: 'image',
            file
          });
        }
        setMedia([...media, ...uploadedMedia]);
        setPostType(uploadedMedia.length > 1 ? 'carousel' : 'photo');
        setPublishStatus({type: null, message: ''});
      } catch (error) {
        console.error('Upload error:', error);
        setPublishStatus({
          type: 'error',
          message: error instanceof Error ? error.message : 'Upload ảnh thất bại'
        });
      }
    }
  };

  const removeMedia = (id: string) => {
    setMedia(media.filter(m => m.id !== id));
    if (media.length === 1) {
      setPostType('text');
    }
  };

  const detectAndPreviewLink = (text: string) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const urls = text.match(urlRegex);
    
    if (urls && urls.length > 0 && !linkPreview) {
      // Mock link preview - in production, fetch OG meta tags
      setTimeout(() => {
        setLinkPreview({
          url: urls[0],
          title: 'Tiêu đề trang web sẽ hiển thị ở đây',
          description: 'Mô tả từ Open Graph meta tags sẽ được tự động lấy khi paste link',
          image: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&h=315&fit=crop'
        });
      }, 500);
    }
  };

  const handleContentChange = (text: string) => {
    setContent(text);
    detectAndPreviewLink(text);
  };

  const togglePageSelection = (pageId: string) => {
    setSelectedPages(prev => 
      prev.includes(pageId) 
        ? prev.filter(id => id !== pageId)
        : [...prev, pageId]
    );
  };

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-gray-900 mb-2">Soạn bài đăng</h2>
        <p className="text-gray-600">Tạo và tùy chỉnh nội dung đăng lên Facebook</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main composer - 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Post type selector */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <label className="block text-sm text-gray-700 mb-4">Loại bài đăng</label>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {postTypes.map((type) => {
                const Icon = type.icon;
                return (
                  <button
                    key={type.id}
                    onClick={() => setPostType(type.id)}
                    className={`p-4 rounded-lg border-2 transition-all text-center ${
                      postType === type.id
                        ? 'bg-blue-50 border-blue-500'
                        : 'bg-white border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Icon className={`w-6 h-6 mx-auto mb-2 ${
                      postType === type.id ? 'text-blue-600' : 'text-gray-400'
                    }`} />
                    <p className={`text-sm mb-1 ${
                      postType === type.id ? 'text-blue-900' : 'text-gray-900'
                    }`}>
                      {type.label}
                    </p>
                    <p className="text-xs text-gray-500">{type.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Content editor */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center gap-2 mb-4">
                <button
                  onClick={() => insertFormatting('bold')}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Bold"
                >
                  <Bold className="w-5 h-5 text-gray-700" />
                </button>
                <button
                  onClick={() => insertFormatting('italic')}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Italic"
                >
                  <Italic className="w-5 h-5 text-gray-700" />
                </button>
                <div className="w-px h-6 bg-gray-300 mx-1" />
                <div className="relative">
                  <button
                    onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    title="Emoji"
                  >
                    <Smile className="w-5 h-5 text-gray-700" />
                  </button>

                  {showEmojiPicker && (
                    <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-10">
                      <div className="grid grid-cols-8 gap-2">
                        {emojis.map((emoji) => (
                          <button
                            key={emoji}
                            onClick={() => insertEmoji(emoji)}
                            className="w-8 h-8 hover:bg-gray-100 rounded flex items-center justify-center"
                          >
                            {emoji}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <div className="w-px h-6 bg-gray-300 mx-1" />
                {/* Quick upload buttons */}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2 hover:bg-green-100 rounded-lg transition-colors"
                  title="Thêm ảnh"
                >
                  <ImageIcon className="w-5 h-5 text-green-600" />
                </button>
                <input
                  ref={videoInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleVideoUpload}
                  className="hidden"
                />
                <button
                  onClick={() => videoInputRef.current?.click()}
                  className="p-2 hover:bg-purple-100 rounded-lg transition-colors"
                  title="Thêm video"
                >
                  <Video className="w-5 h-5 text-purple-600" />
                </button>
                <button
                  onClick={handleAIRewrite}
                  disabled={isLoadingRewrite || !content.trim()}
                  className="ml-auto px-3 py-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isLoadingRewrite ? (
                    <>
                      <div className="w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
                      Đang viết lại...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      AI Rewrite
                    </>
                  )}
                </button>
              </div>
              
              <textarea
                ref={textareaRef}
                value={content}
                onChange={(e) => handleContentChange(e.target.value)}
                placeholder="Bạn đang nghĩ gì?"
                className="w-full min-h-32 p-4 border border-gray-200 rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
                style={{ maxHeight: '70vh' }}
              />

              {/* Preview uploaded media */}
              {media.length > 0 && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-gray-700">
                      {media.length} {media[0].type === 'video' ? 'video' : 'ảnh'} đã chọn
                    </span>
                    <button
                      onClick={() => setMedia([])}
                      className="text-sm text-red-600 hover:text-red-700"
                    >
                      Xóa tất cả
                    </button>
                  </div>
                  <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                    {media.map((item, index) => (
                      <div key={item.id} className="relative aspect-square group">
                        {item.type === 'image' ? (
                          <ImageWithFallback
                            src={item.url}
                            alt={`Upload ${index + 1}`}
                            className="w-full h-full object-cover rounded-lg"
                          />
                        ) : (
                          <div className="w-full h-full bg-gray-900 rounded-lg flex items-center justify-center">
                            <Video className="w-8 h-8 text-white" />
                          </div>
                        )}
                        <button
                          onClick={() => removeMedia(item.id)}
                          className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X className="w-3 h-3 text-white" />
                        </button>
                      </div>
                    ))}
                    {/* Add more button */}
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="aspect-square border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center hover:border-blue-400 hover:bg-blue-50 transition-colors"
                    >
                      <Upload className="w-6 h-6 text-gray-400" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Hashtag suggestions */}
            <div className="p-4 bg-gray-50 border-t border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <Hash className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-700">Hashtag gợi ý:</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {hashtagSuggestions.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => insertHashtag(tag)}
                    className="px-3 py-1 text-sm bg-white border border-gray-200 rounded-full hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* AI Content Generator */}
          <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border-2 border-purple-200 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-6 h-6 text-purple-600" />
              <h3 className="text-gray-900">AI Content Generator</h3>
            </div>

            {/* Prompt Input */}
            <div className="mb-4">
              <label className="block text-sm text-gray-700 mb-2">
                Nhập prompt (yêu cầu của bạn với AI)
              </label>
              <textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                placeholder="Ví dụ: Viết bài đăng quảng cáo sản phẩm giày thể thao, phong cách trẻ trung, kêu gọi mua hàng..."
                className="w-full h-24 p-4 border-2 border-purple-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            {/* AI Options */}
            <div className="mb-4">
              <label className="block text-sm text-gray-700 mb-2">Giọng điệu</label>
              <select
                value={aiTone}
                onChange={(e) => setAiTone(e.target.value as typeof aiTone)}
                className="w-full px-3 py-2 border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="professional">Chuyên nghiệp</option>
                <option value="casual">Thân thiện</option>
                <option value="funny">Hài hước</option>
                <option value="formal">Trang trọng</option>
              </select>
            </div>

            <button
              onClick={handleAIGenerate}
              disabled={!aiPrompt.trim() || isLoadingAI}
              className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
            >
              {isLoadingAI ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Đang tạo nội dung...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Tạo nội dung với AI
                </>
              )}
            </button>
          </div>

          {/* Media upload area */}
          {(postType === 'photo' || postType === 'carousel' || postType === 'video') && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <label className="block text-sm text-gray-700 mb-4">
                {postType === 'video' ? 'Video' : 'Hình ảnh'}
              </label>
              
              {media.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
                  {media.map((item, index) => (
                    <div key={item.id} className="relative aspect-square group">
                      {item.type === 'image' ? (
                        <ImageWithFallback
                          src={item.url}
                          alt={`Upload ${index + 1}`}
                          className="w-full h-full object-cover rounded-lg"
                        />
                      ) : (
                        <div className="w-full h-full bg-gray-900 rounded-lg flex items-center justify-center">
                          <Video className="w-12 h-12 text-white" />
                        </div>
                      )}
                      
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all rounded-lg flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                        <button className="p-2 bg-white rounded-lg hover:bg-gray-100">
                          <Crop className="w-4 h-4 text-gray-700" />
                        </button>
                        <button className="p-2 bg-white rounded-lg hover:bg-gray-100">
                          <Maximize2 className="w-4 h-4 text-gray-700" />
                        </button>
                        <button 
                          onClick={() => removeMedia(item.id)}
                          className="p-2 bg-red-500 rounded-lg hover:bg-red-600"
                        >
                          <X className="w-4 h-4 text-white" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 transition-colors ${
                  dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-gray-50'
                }`}
              >
                <div className="text-center">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-2">
                    Kéo thả file vào đây hoặc
                  </p>
                  <div className="flex gap-2 justify-center">
                    {postType !== 'video' && (
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        Chọn ảnh
                      </button>
                    )}
                    {postType === 'video' && (
                      <button
                        onClick={() => videoInputRef.current?.click()}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                      >
                        Chọn video
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Link preview */}
          {postType === 'link' && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <label className="block text-sm text-gray-700 mb-3">Link URL</label>
              <div className="flex gap-2 mb-4">
                <Link2 className="w-5 h-5 text-gray-400 mt-3" />
                <input
                  type="url"
                  placeholder="https://example.com"
                  className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {linkPreview && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <ImageWithFallback
                    src={linkPreview.image}
                    alt={linkPreview.title}
                    className="w-full h-48 object-cover"
                  />
                  <div className="p-4">
                    <h4 className="text-gray-900 mb-1">{linkPreview.title}</h4>
                    <p className="text-sm text-gray-600 mb-2">{linkPreview.description}</p>
                    <p className="text-xs text-gray-500">{linkPreview.url}</p>
                  </div>
                  <button
                    onClick={() => setLinkPreview(null)}
                    className="w-full py-2 text-sm text-red-600 hover:bg-red-50 border-t border-gray-200"
                  >
                    Xóa preview
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Advanced Settings */}
          <div className="bg-white rounded-lg border border-gray-200">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Settings className="w-5 h-5 text-gray-700" />
                <span className="text-gray-900">Cài đặt nâng cao</span>
              </div>
              {showAdvanced ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </button>

            {showAdvanced && (
              <div className="p-6 pt-0 space-y-6 border-t border-gray-200">
                {/* Interval posting */}
                <div>
                  <label className="flex items-center gap-2 mb-3">
                    <input
                      type="checkbox"
                      checked={intervalPosting}
                      onChange={(e) => setIntervalPosting(e.target.checked)}
                      className="w-4 h-4 text-blue-600"
                    />
                    <Clock className="w-4 h-4 text-gray-700" />
                    <span className="text-sm text-gray-700">Đăng chậm (interval posting)</span>
                  </label>
                  {intervalPosting && (
                    <div className="ml-8">
                      <label className="text-sm text-gray-600 mb-2 block">
                        Khoảng cách giữa mỗi bài (phút)
                      </label>
                      <input
                        type="number"
                        value={intervalMinutes}
                        onChange={(e) => setIntervalMinutes(Number(e.target.value))}
                        min="5"
                        max="1440"
                        className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  )}
                </div>

                {/* UTM Tracking */}
                <div>
                  <label className="block text-sm text-gray-700 mb-3">UTM Tracking</label>
                  <div className="space-y-3">
                    <input
                      type="text"
                      placeholder="utm_source (vd: facebook)"
                      value={utmParams.source}
                      onChange={(e) => setUtmParams({...utmParams, source: e.target.value})}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                      type="text"
                      placeholder="utm_medium (vd: social)"
                      value={utmParams.medium}
                      onChange={(e) => setUtmParams({...utmParams, medium: e.target.value})}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                      type="text"
                      placeholder="utm_campaign (vd: summer_sale)"
                      value={utmParams.campaign}
                      onChange={(e) => setUtmParams({...utmParams, campaign: e.target.value})}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                {/* Location */}
                <div>
                  <label className="flex items-center gap-2 text-sm text-gray-700 mb-3">
                    <MapPin className="w-4 h-4" />
                    Gắn địa điểm
                  </label>
                  <input
                    type="text"
                    placeholder="Tìm địa điểm..."
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* First comment */}
                <div>
                  <label className="flex items-center gap-2 text-sm text-gray-700 mb-3">
                    <MessageSquare className="w-4 h-4" />
                    Comment đầu tiên tự động
                  </label>
                  <textarea
                    placeholder="Nội dung comment sẽ tự động đăng sau khi bài viết được publish..."
                    value={firstComment}
                    onChange={(e) => setFirstComment(e.target.value)}
                    className="w-full h-24 p-4 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Pin post */}
                <div>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={pinPost}
                      onChange={(e) => setPinPost(e.target.checked)}
                      className="w-4 h-4 text-blue-600"
                    />
                    <Pin className="w-4 h-4 text-gray-700" />
                    <span className="text-sm text-gray-700">Ghim bài viết sau khi đăng</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar - 1 column */}
        <div className="space-y-6">
          {/* Page selection */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-gray-900 mb-4">Chọn Page đăng bài</h3>
            
            {selectedPages.length > 0 && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-900">
                  Đã chọn {selectedPages.length} page(s)
                </p>
              </div>
            )}

            <div className="space-y-2 max-h-96 overflow-y-auto">
              {loadingPages ? (
                <div className="text-center py-8">
                  <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-sm text-gray-600 mt-2">Đang tải pages...</p>
                </div>
              ) : pages.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-600">Chưa có page nào được kết nối</p>
                  <p className="text-xs text-gray-500 mt-1">Vui lòng kết nối Facebook page ở tab "Tài khoản"</p>
                </div>
              ) : (
                pages.map((page) => (
                <label 
                  key={page.id} 
                  className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedPages.includes(page.id) 
                      ? 'bg-blue-50 border-2 border-blue-500' 
                      : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedPages.includes(page.id)}
                    onChange={() => togglePageSelection(page.id)}
                    className="w-4 h-4 text-blue-600"
                  />
                  <ImageWithFallback
                    src={page.avatar}
                    alt={page.name}
                    className="w-10 h-10 rounded-full object-cover"
                  />
                  <span className="text-sm text-gray-900 flex-1">{page.name}</span>
                </label>
              ))
              )}
            </div>

            {pages.length > 0 && (
              <button
                onClick={() => {
                  if (selectedPages.length === pages.length) {
                    setSelectedPages([]);
                  } else {
                    setSelectedPages(pages.map(p => p.id));
                  }
                }}
                className="w-full mt-4 py-2 text-sm text-blue-600 hover:text-blue-700"
              >
                {selectedPages.length === pages.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
              </button>
            )}
          </div>

          {/* AI Suggestions */}
          <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg border border-purple-200 p-6">
            <h3 className="text-gray-900 mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-500" />
              AI Insights
            </h3>
            <div className="space-y-3">
              {aiSuggestions.map((suggestion, index) => (
                <div
                  key={index}
                  className="p-3 text-sm text-gray-700 bg-white rounded-lg border border-purple-100"
                >
                  {suggestion}
                </div>
              ))}
            </div>
          </div>

          {/* Status Message */}
          {publishStatus.type && (
            <div className={`p-4 rounded-lg ${
              publishStatus.type === 'success'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}>
              {publishStatus.message}
            </div>
          )}

          {/* Action buttons */}
          <div className="space-y-3">
            <button
              onClick={handlePublish}
              disabled={selectedPages.length === 0 || isPublishing || !content.trim()}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
            >
              {isPublishing ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Đang đăng...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  Đăng ngay
                </>
              )}
            </button>

            <button className="w-full px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center justify-center gap-2 transition-colors">
              <Save className="w-5 h-5" />
              Lưu nháp
            </button>
          </div>

          {/* Preview info */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
            <h4 className="text-sm text-gray-700 mb-3">Thông tin bài viết</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Loại:</span>
                <span className="text-gray-900">{postTypes.find(t => t.id === postType)?.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Ký tự:</span>
                <span className="text-gray-900">{content.length}</span>
              </div>
              {media.length > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Media:</span>
                  <span className="text-gray-900">{media.length} file(s)</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
