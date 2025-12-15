'use client';

import { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { RefreshCw, Trash2, Image as ImageIcon, Calendar, Loader2, Send, Check, Square, CheckSquare, ChevronLeft, ChevronRight, Pencil, X, Save, Bot } from 'lucide-react';
import { agentService, AgentPost } from '@/services/agentService';
import { useAuth } from '@/contexts/AuthContext';

// Dynamic API URL - uses NEXT_PUBLIC_API_URL from env, fallback to same origin
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

// Facebook-style image layout component
interface ImageItem {
  id: number;
  url: string;
  order: number;
}

const FacebookImageLayout = ({ images, layout }: { images: ImageItem[], layout?: string }) => {
  const apiUrl = getApiUrl();

  // Sort images by order to ensure hero image is first
  const sortedImages = [...images].sort((a, b) => a.order - b.order);
  const count = sortedImages.length;

  // Determine layout based on image count if not provided
  const effectiveLayout = layout || (
    count === 1 ? 'single' :
    count === 2 ? 'two_square' :
    count === 3 ? 'one_large_two_small' :
    count === 4 ? 'four_square' :
    'two_large_three_small'
  );

  if (count === 0) return null;

  const renderImage = (img: ImageItem, className: string) => (
    <img
      key={img.id}
      src={`${apiUrl}${img.url}`}
      alt=""
      className={`object-cover ${className}`}
      onError={(e) => {
        e.currentTarget.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" fill="%23f3f4f6"><rect width="100" height="100"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%239ca3af">Error</text></svg>';
      }}
    />
  );

  // Single image - support both frontend and backend layout names
  if (effectiveLayout === 'single' || effectiveLayout === 'single_portrait' ||
      effectiveLayout === 'single_landscape' || effectiveLayout === 'single_square' || count === 1) {
    return (
      <div className="rounded-lg overflow-hidden border border-gray-200">
        {renderImage(sortedImages[0], 'w-full h-auto max-h-[400px]')}
      </div>
    );
  }

  // 2 images - side by side - support both frontend and backend layout names
  if (effectiveLayout === 'two_square' || effectiveLayout === 'two_portrait' || count === 2) {
    return (
      <div className="grid grid-cols-2 gap-1 rounded-lg overflow-hidden border border-gray-200">
        {renderImage(sortedImages[0], 'w-full aspect-square')}
        {renderImage(sortedImages[1], 'w-full aspect-square')}
      </div>
    );
  }

  // 3 images - 1 large (hero) + 2 small - support both frontend and backend layout names
  if (effectiveLayout === 'one_large_two_small' ||
      effectiveLayout === 'one_vertical_two_square' ||
      effectiveLayout === 'one_horizontal_two_square' || count === 3) {
    return (
      <div className="rounded-lg overflow-hidden border border-gray-200">
        <div className="w-full">
          {renderImage(sortedImages[0], 'w-full aspect-[2/1]')}
        </div>
        <div className="grid grid-cols-2 gap-1 mt-1">
          {renderImage(sortedImages[1], 'w-full aspect-square')}
          {renderImage(sortedImages[2], 'w-full aspect-square')}
        </div>
      </div>
    );
  }

  // 4 images - 2x2 grid - support both frontend and backend layout names
  if (effectiveLayout === 'four_square' || effectiveLayout === 'one_vertical_three_square' ||
      effectiveLayout === 'one_horizontal_three_square' || count === 4) {
    return (
      <div className="grid grid-cols-2 gap-1 rounded-lg overflow-hidden border border-gray-200">
        {sortedImages.slice(0, 4).map((img) => renderImage(img, 'w-full aspect-square'))}
      </div>
    );
  }

  // 5+ images - 2 on top + 3 on bottom - support both frontend and backend layout names
  return (
    <div className="rounded-lg overflow-hidden border border-gray-200">
      <div className="grid grid-cols-2 gap-1">
        {renderImage(sortedImages[0], 'w-full aspect-square')}
        {renderImage(sortedImages[1], 'w-full aspect-square')}
      </div>
      <div className="grid grid-cols-3 gap-1 mt-1">
        {sortedImages.slice(2, 5).map((img) => renderImage(img, 'w-full aspect-square'))}
      </div>
      {count > 5 && (
        <div className="text-center text-sm text-gray-500 py-2 bg-gray-100">
          +{count - 5} ảnh khác
        </div>
      )}
    </div>
  );
};

interface FacebookPage {
  id: string;
  name: string;
  avatar: string;
}

export interface AgentPostsGalleryRef {
  refresh: () => void;
}

interface AgentPostsGalleryProps {
  onRequestAgentEdit?: (message: string) => void;
}

export const AgentPostsGallery = forwardRef<AgentPostsGalleryRef, AgentPostsGalleryProps>(({ onRequestAgentEdit }, ref) => {
  const [posts, setPosts] = useState<AgentPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedPost, setSelectedPost] = useState<AgentPost | null>(null);

  // Publishing states
  const { tokens } = useAuth();
  const [selectedPostIds, setSelectedPostIds] = useState<number[]>([]);
  const [pages, setPages] = useState<FacebookPage[]>([]);
  const [selectedPages, setSelectedPages] = useState<string[]>([]);
  const [loadingPages, setLoadingPages] = useState(true);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishStatus, setPublishStatus] = useState<{type: 'success' | 'error' | null, message: string}>({type: null, message: ''});
  const [showPublishPanel, setShowPublishPanel] = useState(false);

  // Carousel states - track current image index per post
  const [carouselIndexes, setCarouselIndexes] = useState<{[postId: number]: number}>({});
  const [detailImageIndex, setDetailImageIndex] = useState(0);
  const [showImageLightbox, setShowImageLightbox] = useState(false);

  // Image selection for publish - track selected image IDs per post
  const [selectedImageIds, setSelectedImageIds] = useState<{[postId: number]: number[]}>({});

  // Edit mode states
  const [isEditMode, setIsEditMode] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [editFullContent, setEditFullContent] = useState('');
  const [editHashtags, setEditHashtags] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadPosts();
  }, []);

  // Fetch Facebook pages
  useEffect(() => {
    const fetchPages = async () => {
      if (!tokens) return;

      setLoadingPages(true);
      try {
        const response = await fetch(`${getApiUrl()}/api/platforms/accounts?platform=facebook`, {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`
          }
        });

        if (response.ok) {
          const data = await response.json();
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
  }, [tokens]);

  const loadPosts = async () => {
    try {
      setIsLoading(true);
      const data = await agentService.getPosts(20);
      setPosts(data);
    } catch (error) {
      console.error('Failed to load posts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadPosts();
    setIsRefreshing(false);
  };

  // Expose refresh method to parent via ref
  useImperativeHandle(ref, () => ({
    refresh: handleRefresh
  }));

  const handleDelete = async (postId: number) => {
    if (!confirm('Bạn có chắc muốn xóa bài đăng này?')) return;

    try {
      await agentService.deletePost(postId);
      setPosts(prev => prev.filter(p => p.id !== postId));
      if (selectedPost?.id === postId) {
        setSelectedPost(null);
      }
      // Also remove from selected posts
      setSelectedPostIds(prev => prev.filter(id => id !== postId));
    } catch (error) {
      console.error('Failed to delete post:', error);
      alert('Không thể xóa bài đăng. Vui lòng thử lại.');
    }
  };

  // Enter edit mode
  const handleStartEdit = () => {
    if (!selectedPost) return;
    setEditContent(selectedPost.content || '');
    setEditFullContent(selectedPost.full_content || '');
    setEditHashtags((selectedPost.hashtags || []).join(', '));
    setIsEditMode(true);
  };

  // Cancel edit
  const handleCancelEdit = () => {
    setIsEditMode(false);
    setEditContent('');
    setEditFullContent('');
    setEditHashtags('');
  };

  // Save edit
  const handleSaveEdit = async () => {
    if (!selectedPost) return;

    setIsSaving(true);
    try {
      // Parse hashtags from comma-separated string
      const hashtagsArray = editHashtags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0)
        .map(tag => tag.startsWith('#') ? tag : `#${tag}`);

      const updatedPost = await agentService.updatePost(selectedPost.id, {
        content: editContent,
        full_content: editFullContent,
        hashtags: hashtagsArray
      });

      // Update in posts list
      setPosts(prev => prev.map(p =>
        p.id === selectedPost.id ? { ...p, ...updatedPost } : p
      ));

      // Update selected post
      setSelectedPost(prev => prev ? { ...prev, ...updatedPost } : null);

      setIsEditMode(false);
      alert('Đã lưu thay đổi!');
    } catch (error) {
      console.error('Failed to update post:', error);
      alert('Không thể lưu thay đổi. Vui lòng thử lại.');
    } finally {
      setIsSaving(false);
    }
  };

  // Toggle post selection
  const togglePostSelection = (postId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedPostIds(prev =>
      prev.includes(postId)
        ? prev.filter(id => id !== postId)
        : [...prev, postId]
    );
  };

  // Toggle page selection
  const togglePageSelection = (pageId: string) => {
    setSelectedPages(prev =>
      prev.includes(pageId)
        ? prev.filter(id => id !== pageId)
        : [...prev, pageId]
    );
  };

  // Select all posts
  const selectAllPosts = () => {
    if (selectedPostIds.length === posts.length) {
      setSelectedPostIds([]);
    } else {
      setSelectedPostIds(posts.map(p => p.id));
    }
  };

  // Publish selected posts - use target_account of each post if available
  const handlePublish = async () => {
    if (!tokens || selectedPostIds.length === 0) {
      setPublishStatus({type: 'error', message: 'Vui lòng chọn bài đăng để đăng'});
      return;
    }

    // Check if all posts have target_account or user has selected pages
    const postsWithoutTarget = selectedPostIds.filter(id => {
      const post = posts.find(p => p.id === id);
      return !post?.target_account;
    });

    if (postsWithoutTarget.length > 0 && selectedPages.length === 0) {
      setPublishStatus({
        type: 'error',
        message: `Có ${postsWithoutTarget.length} bài chưa được gắn page. Vui lòng chọn page mặc định để đăng.`
      });
      return;
    }

    setIsPublishing(true);
    setPublishStatus({type: null, message: ''});

    let successCount = 0;
    let failCount = 0;
    const publishedPages = new Set<string>();

    try {
      for (const postId of selectedPostIds) {
        const post = posts.find(p => p.id === postId);
        if (!post) continue;

        // Determine target page(s):
        // - If post has target_account: use that
        // - Otherwise: use selectedPages (user selection)
        const targetAccountIds = post.target_account
          ? [post.target_account.id]
          : selectedPages.map(id => parseInt(id));

        if (targetAccountIds.length === 0) {
          failCount++;
          continue;
        }

        // Track which pages we're publishing to
        if (post.target_account) {
          publishedPages.add(post.target_account.name);
        } else {
          selectedPages.forEach(pageId => {
            const page = pages.find(p => p.id === pageId);
            if (page) publishedPages.add(page.name);
          });
        }

        // Get selected images for this post - sort by order to ensure hero image is first
        const images = [...(post.images || [])].sort((a, b) => a.order - b.order);
        const selectedImagesForPost = selectedImageIds[postId] || images.map(img => img.id);

        // Get URLs of selected images
        const selectedImageUrls = images
          .filter(img => selectedImagesForPost.includes(img.id))
          .map(img => img.url);

        // Fallback to image_url if no images array
        const mediaUrls = selectedImageUrls.length > 0
          ? selectedImageUrls
          : (post.image_url ? [post.image_url] : []);

        try {
          // Step 1: Create post
          const createResponse = await fetch(`${getApiUrl()}/api/platforms/posts`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              content: post.full_content || post.content,
              title: '',
              media_urls: mediaUrls,
              media_type: mediaUrls.length > 0 ? 'image' : 'none',
              link_url: null,
              target_account_ids: targetAccountIds,
              scheduled_at: null
            })
          });

          if (!createResponse.ok) {
            failCount++;
            continue;
          }

          const createdPost = await createResponse.json();

          // Step 2: Publish post
          const publishResponse = await fetch(`${getApiUrl()}/api/platforms/posts/${createdPost.id}/publish`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${tokens.access_token}`,
              'Content-Type': 'application/json'
            }
          });

          if (publishResponse.ok) {
            successCount++;
          } else {
            failCount++;
          }
        } catch {
          failCount++;
        }
      }

      if (successCount > 0) {
        const pageNames = Array.from(publishedPages).slice(0, 3).join(', ');
        const morePages = publishedPages.size > 3 ? ` và ${publishedPages.size - 3} page khác` : '';
        setPublishStatus({
          type: 'success',
          message: `Đã đăng thành công ${successCount} bài lên ${pageNames}${morePages}!${failCount > 0 ? ` (${failCount} bài thất bại)` : ''}`
        });
        // Clear selections after successful publish
        setSelectedPostIds([]);
        setSelectedImageIds({});
        setShowPublishPanel(false);
      } else {
        setPublishStatus({
          type: 'error',
          message: 'Đăng bài thất bại. Vui lòng thử lại.'
        });
      }
    } catch (error) {
      console.error('Publish error:', error);
      setPublishStatus({
        type: 'error',
        message: 'Đã xảy ra lỗi khi đăng bài'
      });
    } finally {
      setIsPublishing(false);
    }
  };

  // Carousel navigation for grid cards
  const handleCardCarouselPrev = (postId: number, totalImages: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setCarouselIndexes(prev => ({
      ...prev,
      [postId]: ((prev[postId] || 0) - 1 + totalImages) % totalImages
    }));
  };

  const handleCardCarouselNext = (postId: number, totalImages: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setCarouselIndexes(prev => ({
      ...prev,
      [postId]: ((prev[postId] || 0) + 1) % totalImages
    }));
  };

  const renderPostCard = (post: AgentPost) => {
    const isSelected = selectedPostIds.includes(post.id);
    // Sort images by order to ensure hero image is first
    const images = [...(post.images || [])].sort((a, b) => a.order - b.order);
    const hasMultipleImages = images.length > 1;
    const currentImageIndex = carouselIndexes[post.id] || 0;

    // Get current image URL - prefer images array, fallback to image_url
    const currentImageUrl = images.length > 0
      ? images[currentImageIndex]?.url
      : post.image_url;

    return (
      <div
        key={post.id}
        onClick={() => {
          setSelectedPost(post);
          setDetailImageIndex(0); // Reset detail carousel when selecting new post
        }}
        className={`bg-white rounded-lg border-2 overflow-hidden cursor-pointer hover:shadow-lg transition-all ${
          isSelected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200'
        }`}
      >
        {/* Image Carousel with checkbox overlay */}
        {currentImageUrl ? (
          <div className="aspect-square bg-gray-100 relative group">
            <img
              src={`${getApiUrl()}${currentImageUrl}`}
              alt="Post image"
              className="w-full h-full object-cover"
              onError={(e) => {
                console.error('Grid image load error:', currentImageUrl);
                e.currentTarget.style.display = 'none';
                e.currentTarget.parentElement!.innerHTML = '<div class="w-full h-full flex items-center justify-center bg-gray-200"><svg class="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg></div>';
              }}
            />

            {/* Carousel Navigation - only show if multiple images */}
            {hasMultipleImages && (
              <>
                {/* Left Arrow */}
                <button
                  onClick={(e) => handleCardCarouselPrev(post.id, images.length, e)}
                  className="absolute left-1 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                {/* Right Arrow */}
                <button
                  onClick={(e) => handleCardCarouselNext(post.id, images.length, e)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
                {/* Dots Indicator */}
                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                  {images.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={(e) => {
                        e.stopPropagation();
                        setCarouselIndexes(prev => ({ ...prev, [post.id]: idx }));
                      }}
                      className={`w-2 h-2 rounded-full transition-all ${
                        idx === currentImageIndex ? 'bg-white w-4' : 'bg-white/50'
                      }`}
                    />
                  ))}
                </div>
                {/* Image Counter Badge */}
                <div className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded-full">
                  {currentImageIndex + 1}/{images.length}
                </div>
              </>
            )}

            {/* Checkbox overlay */}
            <button
              onClick={(e) => togglePostSelection(post.id, e)}
              className={`absolute top-2 left-2 w-6 h-6 rounded flex items-center justify-center transition-all ${
                isSelected
                  ? 'bg-blue-500 text-white'
                  : 'bg-white/80 hover:bg-white text-gray-400 hover:text-gray-600 border border-gray-300'
              }`}
            >
              {isSelected ? <Check className="w-4 h-4" /> : <Square className="w-4 h-4" />}
            </button>
          </div>
        ) : (
          <div className="aspect-square bg-gradient-to-br from-purple-100 to-pink-100 flex items-center justify-center relative">
            <ImageIcon className="w-16 h-16 text-gray-400" />
            {/* Checkbox overlay for no-image posts */}
            <button
              onClick={(e) => togglePostSelection(post.id, e)}
              className={`absolute top-2 left-2 w-6 h-6 rounded flex items-center justify-center transition-all ${
                isSelected
                  ? 'bg-blue-500 text-white'
                  : 'bg-white/80 hover:bg-white text-gray-400 hover:text-gray-600 border border-gray-300'
              }`}
            >
              {isSelected ? <Check className="w-4 h-4" /> : <Square className="w-4 h-4" />}
            </button>
          </div>
        )}

        {/* Content Preview */}
        <div className="p-4">
          {/* Post ID Badge + Target Page */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
              #{post.id}
            </span>
            {post.target_account && (
              <div className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                {post.target_account.profile_picture_url ? (
                  <img
                    src={post.target_account.profile_picture_url}
                    alt=""
                    className="w-4 h-4 rounded-full"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                ) : null}
                <span className="truncate max-w-[80px]" title={post.target_account.name}>
                  {post.target_account.name}
                </span>
              </div>
            )}
          </div>
          <p className="text-sm text-gray-700 line-clamp-3">{post.content}</p>

          {/* Hashtags */}
          {post.hashtags && post.hashtags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {post.hashtags.slice(0, 3).map((tag, idx) => (
                <span
                  key={idx}
                  className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full"
                >
                  {tag}
                </span>
              ))}
              {post.hashtags.length > 3 && (
                <span className="text-xs text-gray-500">+{post.hashtags.length - 3}</span>
              )}
            </div>
          )}

          {/* Meta */}
          <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {new Date(post.created_at).toLocaleDateString('vi-VN')}
            </div>
            <button
              onClick={e => {
                e.stopPropagation();
                handleDelete(post.id);
              }}
              className="text-red-500 hover:text-red-700 p-1"
              title="Xóa"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full bg-gray-50 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Bài đăng Fugu đã tạo
              </h2>
              <p className="text-sm text-gray-500">
                {posts.length} bài đăng
                {selectedPostIds.length > 0 && (
                  <span className="ml-2 text-blue-600 font-medium">
                    • Đã chọn {selectedPostIds.length} bài
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* Select All Button */}
              {posts.length > 0 && (
                <button
                  onClick={selectAllPosts}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  {selectedPostIds.length === posts.length ? (
                    <>
                      <CheckSquare className="w-4 h-4" />
                      Bỏ chọn tất cả
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
              {selectedPostIds.length > 0 && (
                <button
                  onClick={() => {
                    const postIdsText = selectedPostIds.map(id => `#${id}`).join(', ');
                    const context = `Tôi muốn sửa các bài đăng ${postIdsText}`;
                    if (onRequestAgentEdit) {
                      onRequestAgentEdit(context);
                    }
                  }}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                >
                  <Bot className="w-4 h-4" />
                  Nhờ Fugu sửa ({selectedPostIds.length})
                </button>
              )}

              {/* Publish Button */}
              {selectedPostIds.length > 0 && (
                <button
                  onClick={() => setShowPublishPanel(true)}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Send className="w-4 h-4" />
                  Đăng bài ({selectedPostIds.length})
                </button>
              )}

              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw
                  className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`}
                />
                Làm mới
              </button>
            </div>
          </div>

          {/* Publish Status Message */}
          {publishStatus.type && (
            <div className={`mt-3 p-3 rounded-lg ${
              publishStatus.type === 'success'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}>
              {publishStatus.message}
            </div>
          )}
        </div>

        {/* Posts Grid */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : posts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center mb-4">
                <ImageIcon className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                Chưa có bài đăng nào
              </h3>
              <p className="text-gray-500 max-w-md">
                Fugu chưa tạo bài đăng nào. Hãy chat với Fugu và yêu cầu tạo bài đăng!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {posts.map(renderPostCard)}
            </div>
          )}
        </div>

      {/* Post Detail Slide-over */}
      {selectedPost && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/30 z-40 transition-opacity"
            onClick={() => { setSelectedPost(null); setShowImageLightbox(false); }}
          />
          {/* Slide-over Panel */}
          <div className="fixed inset-y-0 right-0 w-full max-w-lg bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between shrink-0">
              <h3 className="text-lg font-semibold text-gray-800">
                {isEditMode ? 'Chỉnh sửa bài đăng' : 'Chi tiết bài đăng'}
              </h3>
              <div className="flex items-center gap-2">
                {isEditMode ? (
                  <>
                    <button
                      onClick={handleCancelEdit}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4" />
                      Hủy
                    </button>
                    <button
                      onClick={handleSaveEdit}
                      disabled={isSaving}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                      {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      Lưu
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleStartEdit}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <Pencil className="w-4 h-4" />
                    Sửa nhanh
                  </button>
                )}
                <button
                  onClick={() => { setSelectedPost(null); handleCancelEdit(); setShowImageLightbox(false); }}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Facebook-style Image Layout */}
            {(() => {
              // Sort images by order to ensure hero image is first
              const images = [...(selectedPost.images || [])].sort((a, b) => a.order - b.order);
              const hasImages = images.length > 0 || selectedPost.image_url;
              const layout = selectedPost.generation_strategy?.layout;

              if (!hasImages) return null;

              // If only 1 image or single image_url, show simple view with click to enlarge
              if (images.length === 0 && selectedPost.image_url) {
                return (
                  <div
                    className="rounded-lg overflow-hidden border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity"
                    onClick={() => {
                      // For single image_url, we'll show it in a simple lightbox
                      setShowImageLightbox(true);
                    }}
                  >
                    <img
                      src={`${getApiUrl()}${selectedPost.image_url}`}
                      alt="Post image"
                      className="w-full h-auto max-h-[400px] object-contain"
                    />
                    <p className="text-xs text-gray-500 text-center py-1 bg-gray-50">Click để phóng to</p>
                  </div>
                );
              }

              // If only 1 image in images array
              if (images.length === 1) {
                return (
                  <div
                    className="rounded-lg overflow-hidden border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity"
                    onClick={() => {
                      setDetailImageIndex(0);
                      setShowImageLightbox(true);
                    }}
                  >
                    <img
                      src={`${getApiUrl()}${images[0].url}`}
                      alt="Post image"
                      className="w-full h-auto max-h-[400px] object-contain"
                    />
                    <p className="text-xs text-gray-500 text-center py-1 bg-gray-50">Click để phóng to</p>
                  </div>
                );
              }

              // Show Facebook-style layout for multiple images
              return (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-700">
                      Bố cục Facebook ({images.length} ảnh)
                    </h4>
                    {layout && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                        {layout}
                      </span>
                    )}
                  </div>
                  <FacebookImageLayout images={images} layout={layout} />

                  {/* Thumbnails for individual viewing */}
                  {images.length > 1 && (
                    <div className="pt-2 border-t border-gray-200">
                      <p className="text-xs text-gray-500 mb-2">Xem từng ảnh (click để phóng to):</p>
                      <div className="flex gap-2 overflow-x-auto pb-2">
                        {images.map((img, idx) => (
                          <button
                            key={img.id}
                            onClick={() => {
                              setDetailImageIndex(idx);
                              setShowImageLightbox(true);
                            }}
                            className={`flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all hover:scale-105 ${
                              idx === detailImageIndex
                                ? 'border-blue-500 ring-2 ring-blue-200'
                                : 'border-gray-200 hover:border-blue-400'
                            }`}
                          >
                            <img
                              src={`${getApiUrl()}${img.url}`}
                              alt={`Thumbnail ${idx + 1}`}
                              className="w-full h-full object-cover"
                            />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Content - Editable in edit mode */}
            <div>
              <h4 className="text-base font-semibold text-gray-700 mb-3">Nội dung:</h4>
              {isEditMode ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={4}
                  placeholder="Nhập nội dung bài đăng..."
                />
              ) : (
                <p className="text-gray-800 whitespace-pre-wrap text-base leading-relaxed">
                  {selectedPost.content}
                </p>
              )}
            </div>

            {/* Hashtags - Editable in edit mode */}
            <div>
              <h4 className="text-base font-semibold text-gray-700 mb-3">Hashtags:</h4>
              {isEditMode ? (
                <input
                  type="text"
                  value={editHashtags}
                  onChange={(e) => setEditHashtags(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Nhập hashtags, cách nhau bằng dấu phẩy..."
                />
              ) : selectedPost.hashtags && selectedPost.hashtags.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {selectedPost.hashtags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="text-base text-blue-600 bg-blue-50 px-3 py-1.5 rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 text-sm">Chưa có hashtags</p>
              )}
            </div>

            {/* Full Content - Editable in edit mode */}
            <div>
              <h4 className="text-base font-semibold text-gray-700 mb-3">
                Nội dung đầy đủ:
              </h4>
              {isEditMode ? (
                <textarea
                  value={editFullContent}
                  onChange={(e) => setEditFullContent(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={8}
                  placeholder="Nhập nội dung đầy đủ..."
                />
              ) : selectedPost.full_content && selectedPost.full_content.trim() ? (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <p className="text-gray-700 whitespace-pre-wrap text-base leading-relaxed">
                    {selectedPost.full_content}
                  </p>
                </div>
              ) : (
                <p className="text-gray-400 text-sm">Chưa có nội dung đầy đủ</p>
              )}
            </div>

            {/* Agent Reasoning */}
            {selectedPost.agent_reasoning && selectedPost.agent_reasoning.trim() && (
              <div>
                <h4 className="text-base font-semibold text-gray-700 mb-3">
                  Lý do của Fugu:
                </h4>
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                  <p className="text-gray-700 whitespace-pre-wrap text-sm leading-relaxed">
                    {selectedPost.agent_reasoning}
                  </p>
                </div>
              </div>
            )}

            {/* Generation Strategy */}
            {selectedPost.generation_strategy && Object.keys(selectedPost.generation_strategy).length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-gray-700 mb-3">
                  Chiến lược tạo bài:
                </h4>
                <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-x-auto">
                    {JSON.stringify(selectedPost.generation_strategy, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Meta Info */}
            <div className="text-sm text-gray-500 space-y-2 pt-4 border-t border-gray-200">
              <p>
                <span className="font-semibold">Tạo lúc:</span>{' '}
                {new Date(selectedPost.created_at).toLocaleString('vi-VN')}
              </p>
              {selectedPost.completed_at && (
                <p>
                  <span className="font-semibold">Hoàn thành:</span>{' '}
                  {new Date(selectedPost.completed_at).toLocaleString('vi-VN')}
                </p>
              )}
              <p>
                <span className="font-semibold">Trạng thái:</span>{' '}
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs ${
                    selectedPost.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {selectedPost.status}
                </span>
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="px-6 py-4 border-t border-gray-200 shrink-0 space-y-2">
            {!isEditMode && (
              <>
                {/* Nhờ Agent sửa button */}
                <button
                  onClick={() => {
                    // Prepare context message for agent
                    const context = `Tôi muốn sửa bài đăng #${selectedPost.id}`;
                    // Close slide-over and send to agent
                    setSelectedPost(null);
                    if (onRequestAgentEdit) {
                      onRequestAgentEdit(context);
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
                >
                  <Bot className="w-4 h-4" />
                  Nhờ Fugu sửa (có thể tạo ảnh mới)
                </button>
                <button
                  onClick={() => handleDelete(selectedPost.id)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Xóa bài đăng
                </button>
              </>
            )}
          </div>
          </div>
        </>
      )}

      {/* Image Lightbox Modal */}
      {showImageLightbox && selectedPost && (
        (() => {
          // Sort images by order to ensure hero image is first
          const images = [...(selectedPost.images || [])].sort((a, b) => a.order - b.order);
          // Handle single image_url case (no images array)
          const hasSingleImageUrl = images.length === 0 && selectedPost.image_url;

          if (images.length === 0 && !hasSingleImageUrl) return null;

          // For single image_url, create a pseudo image object
          const displayImages = hasSingleImageUrl
            ? [{ id: 0, url: selectedPost.image_url!, order: 0 }]
            : images;

          const currentImage = displayImages[detailImageIndex];
          if (!currentImage) return null;

          return (
            <div
              className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center"
              onClick={() => setShowImageLightbox(false)}
            >
              {/* Close button */}
              <button
                onClick={() => setShowImageLightbox(false)}
                className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors z-10"
              >
                <X className="w-6 h-6" />
              </button>

              {/* Image counter - only show if multiple images */}
              {displayImages.length > 1 && (
                <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1 rounded-full text-sm">
                  {detailImageIndex + 1} / {displayImages.length}
                </div>
              )}

              {/* Previous button */}
              {displayImages.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDetailImageIndex((prev) => (prev - 1 + displayImages.length) % displayImages.length);
                  }}
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
                >
                  <ChevronLeft className="w-8 h-8" />
                </button>
              )}

              {/* Main image */}
              <img
                src={`${getApiUrl()}${currentImage.url}`}
                alt={`Image ${detailImageIndex + 1}`}
                className="max-w-[90vw] max-h-[85vh] object-contain rounded-lg shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              />

              {/* Next button */}
              {displayImages.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDetailImageIndex((prev) => (prev + 1) % displayImages.length);
                  }}
                  className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors"
                >
                  <ChevronRight className="w-8 h-8" />
                </button>
              )}

              {/* Thumbnail strip at bottom - only show if multiple images */}
              {displayImages.length > 1 && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 bg-black/50 p-2 rounded-lg">
                  {displayImages.map((img, idx) => (
                    <button
                      key={img.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        setDetailImageIndex(idx);
                      }}
                      className={`w-12 h-12 rounded overflow-hidden border-2 transition-all ${
                        idx === detailImageIndex
                          ? 'border-white scale-110'
                          : 'border-transparent opacity-60 hover:opacity-100'
                      }`}
                    >
                      <img
                        src={`${getApiUrl()}${img.url}`}
                        alt={`Thumb ${idx + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })()
      )}

      {/* Publish Panel Modal */}
      {showPublishPanel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 max-h-[80vh] flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Đăng bài lên Facebook</h3>
                <p className="text-sm text-gray-500">{selectedPostIds.length} bài đăng đã chọn</p>
              </div>
              <button
                onClick={() => {
                  setShowPublishPanel(false);
                  setPublishStatus({type: null, message: ''});
                }}
                className="text-gray-400 hover:text-gray-600 text-xl p-1"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Summary: Posts with/without target account */}
              {(() => {
                const postsWithTarget = selectedPostIds.filter(id => posts.find(p => p.id === id)?.target_account);
                const postsWithoutTarget = selectedPostIds.filter(id => !posts.find(p => p.id === id)?.target_account);

                return (
                  <>
                    {/* Posts with target account - will auto publish */}
                    {postsWithTarget.length > 0 && (
                      <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <h4 className="text-sm font-medium text-green-700 mb-2">
                          ✓ {postsWithTarget.length} bài đã được gắn page
                        </h4>
                        <p className="text-xs text-green-600">
                          Sẽ tự động đăng lên page được gắn của từng bài
                        </p>
                      </div>
                    )}

                    {/* Posts without target account - need to select pages */}
                    {postsWithoutTarget.length > 0 && (
                      <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <h4 className="text-sm font-medium text-yellow-700 mb-2">
                          ⚠ {postsWithoutTarget.length} bài chưa được gắn page
                        </h4>
                        <p className="text-xs text-yellow-600">
                          Vui lòng chọn page mặc định bên dưới để đăng các bài này
                        </p>
                      </div>
                    )}
                  </>
                );
              })()}

              {/* Page selection - only show if there are posts without target */}
              {(() => {
                const postsWithoutTarget = selectedPostIds.filter(id => !posts.find(p => p.id === id)?.target_account);
                if (postsWithoutTarget.length === 0) return null;

                return (
                  <>
                    <h4 className="text-sm font-medium text-gray-700 mb-3">Chọn Page mặc định cho bài chưa gắn:</h4>

                    {loadingPages ? (
                      <div className="text-center py-8">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto" />
                        <p className="text-sm text-gray-600 mt-2">Đang tải danh sách pages...</p>
                      </div>
                    ) : pages.length === 0 ? (
                      <div className="text-center py-8 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-600">Chưa có page nào được kết nối</p>
                        <p className="text-xs text-gray-500 mt-1">Vui lòng kết nối Facebook page ở tab "Tài khoản"</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {pages.map((page) => (
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
                              className="w-4 h-4 text-blue-600 rounded"
                            />
                            <img
                              src={page.avatar}
                              alt={page.name}
                              className="w-10 h-10 rounded-full object-cover"
                              onError={(e) => {
                                e.currentTarget.src = 'https://via.placeholder.com/100?text=Page';
                              }}
                            />
                            <span className="text-sm text-gray-900 flex-1">{page.name}</span>
                          </label>
                        ))}
                      </div>
                    )}

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
                        {selectedPages.length === pages.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả pages'}
                      </button>
                    )}
                  </>
                );
              })()}

              {/* Selected posts preview with image selection */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Chi tiết bài đăng:</h4>
                <div className="space-y-4 max-h-60 overflow-y-auto">
                  {selectedPostIds.map(postId => {
                    const post = posts.find(p => p.id === postId);
                    if (!post) return null;

                    // Sort images by order to ensure hero image is first
                    const images = [...(post.images || [])].sort((a, b) => a.order - b.order);
                    const hasMultipleImages = images.length > 1;
                    const selectedImagesForPost = selectedImageIds[postId] || images.map(img => img.id);

                    // Toggle image selection for this post
                    const toggleImageForPost = (imageId: number) => {
                      setSelectedImageIds(prev => {
                        const current = prev[postId] || images.map(img => img.id);
                        const updated = current.includes(imageId)
                          ? current.filter(id => id !== imageId)
                          : [...current, imageId];
                        return { ...prev, [postId]: updated };
                      });
                    };

                    return (
                      <div key={postId} className="p-3 bg-gray-50 rounded-lg">
                        {/* Target page badge */}
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-gray-400">#{postId}</span>
                          {post.target_account ? (
                            <div className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">
                              {post.target_account.profile_picture_url && (
                                <img
                                  src={post.target_account.profile_picture_url}
                                  alt=""
                                  className="w-4 h-4 rounded-full"
                                />
                              )}
                              <span>→ {post.target_account.name}</span>
                            </div>
                          ) : (
                            <span className="text-xs text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded">
                              → Page mặc định
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-600 line-clamp-2 mb-2">{post.content}</p>

                        {/* Image selection grid */}
                        {images.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {images.map((img) => {
                              const isImageSelected = selectedImagesForPost.includes(img.id);
                              return (
                                <button
                                  key={img.id}
                                  onClick={() => hasMultipleImages && toggleImageForPost(img.id)}
                                  className={`relative w-14 h-14 rounded overflow-hidden border-2 transition-all ${
                                    isImageSelected
                                      ? 'border-blue-500 ring-2 ring-blue-200'
                                      : 'border-gray-300 opacity-50'
                                  } ${hasMultipleImages ? 'cursor-pointer hover:opacity-100' : 'cursor-default'}`}
                                >
                                  <img
                                    src={`${getApiUrl()}${img.url}`}
                                    alt=""
                                    className="w-full h-full object-cover"
                                  />
                                  {hasMultipleImages && (
                                    <div className={`absolute inset-0 flex items-center justify-center ${
                                      isImageSelected ? 'bg-blue-500/30' : 'bg-black/30'
                                    }`}>
                                      {isImageSelected ? (
                                        <Check className="w-4 h-4 text-white" />
                                      ) : (
                                        <Square className="w-4 h-4 text-white" />
                                      )}
                                    </div>
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        ) : post.image_url ? (
                          <img
                            src={`${getApiUrl()}${post.image_url}`}
                            alt=""
                            className="w-14 h-14 rounded object-cover"
                          />
                        ) : (
                          <div className="w-14 h-14 rounded bg-gray-200 flex items-center justify-center">
                            <ImageIcon className="w-5 h-5 text-gray-400" />
                          </div>
                        )}

                        {hasMultipleImages && (
                          <p className="text-xs text-blue-600 mt-2">
                            Đã chọn {selectedImagesForPost.length}/{images.length} ảnh
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-200 space-y-3">
              {publishStatus.type && (
                <div className={`p-3 rounded-lg text-sm ${
                  publishStatus.type === 'success'
                    ? 'bg-green-50 text-green-700'
                    : 'bg-red-50 text-red-700'
                }`}>
                  {publishStatus.message}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowPublishPanel(false);
                    setPublishStatus({type: null, message: ''});
                  }}
                  className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Hủy
                </button>
                {(() => {
                  // Check if all posts have target_account
                  const postsWithoutTarget = selectedPostIds.filter(id => !posts.find(p => p.id === id)?.target_account);
                  const canPublish = postsWithoutTarget.length === 0 || selectedPages.length > 0;

                  return (
                    <button
                      onClick={handlePublish}
                      disabled={!canPublish || isPublishing}
                      className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
                    >
                      {isPublishing ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Đang đăng...
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          Đăng ngay
                        </>
                      )}
                    </button>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

AgentPostsGallery.displayName = 'AgentPostsGallery';
