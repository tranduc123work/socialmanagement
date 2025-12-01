'use client';

import { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { RefreshCw, Trash2, Image as ImageIcon, Calendar, Loader2, Send, Check, Square, CheckSquare } from 'lucide-react';
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

interface FacebookPage {
  id: string;
  name: string;
  avatar: string;
}

export interface AgentPostsGalleryRef {
  refresh: () => void;
}

export const AgentPostsGallery = forwardRef<AgentPostsGalleryRef>((_props, ref) => {
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

  // Publish selected posts to selected pages
  const handlePublish = async () => {
    if (!tokens || selectedPostIds.length === 0 || selectedPages.length === 0) {
      setPublishStatus({type: 'error', message: 'Vui lòng chọn bài đăng và page để đăng'});
      return;
    }

    setIsPublishing(true);
    setPublishStatus({type: null, message: ''});

    let successCount = 0;
    let failCount = 0;

    try {
      for (const postId of selectedPostIds) {
        const post = posts.find(p => p.id === postId);
        if (!post) continue;

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
              media_urls: post.image_url ? [post.image_url] : [],
              media_type: post.image_url ? 'image' : 'none',
              link_url: null,
              target_account_ids: selectedPages.map(id => parseInt(id)),
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
        setPublishStatus({
          type: 'success',
          message: `Đã đăng thành công ${successCount} bài lên ${selectedPages.length} page(s)!${failCount > 0 ? ` (${failCount} bài thất bại)` : ''}`
        });
        // Clear selections after successful publish
        setSelectedPostIds([]);
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

  const renderPostCard = (post: AgentPost) => {
    const isSelected = selectedPostIds.includes(post.id);
    return (
      <div
        key={post.id}
        onClick={() => setSelectedPost(post)}
        className={`bg-white rounded-lg border-2 overflow-hidden cursor-pointer hover:shadow-lg transition-all ${
          isSelected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-200'
        }`}
      >
        {/* Image with checkbox overlay */}
        {post.image_url ? (
          <div className="aspect-square bg-gray-100 relative">
            <img
              src={`${getApiUrl()}${post.image_url}`}
              alt="Post image"
              className="w-full h-full object-cover"
              onError={(e) => {
                console.error('Grid image load error:', post.image_url);
                e.currentTarget.style.display = 'none';
                e.currentTarget.parentElement!.innerHTML = '<div class="w-full h-full flex items-center justify-center bg-gray-200"><svg class="w-16 h-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg></div>';
              }}
            />
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
    <div className="flex h-full bg-gray-50">
      {/* Posts Grid */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Bài đăng Agent đã tạo
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
                Agent chưa tạo bài đăng nào. Hãy chat với Agent và yêu cầu tạo bài đăng!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {posts.map(renderPostCard)}
            </div>
          )}
        </div>
      </div>

      {/* Post Detail Sidebar - Larger */}
      {selectedPost && (
        <div className="w-[600px] bg-white border-l border-gray-200 flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-800">Chi tiết bài đăng</h3>
            <button
              onClick={() => setSelectedPost(null)}
              className="text-gray-400 hover:text-gray-600 text-xl"
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Image - Larger */}
            {selectedPost.image_url && (
              <div className="rounded-lg overflow-hidden border border-gray-200 bg-gray-100">
                <img
                  src={`${getApiUrl()}${selectedPost.image_url}`}
                  alt="Post image"
                  className="w-full h-auto max-h-[400px] object-contain"
                  onError={(e) => {
                    console.error('Image load error:', selectedPost.image_url);
                    e.currentTarget.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text x="50%" y="50%" text-anchor="middle" dy=".3em">Image Error</text></svg>';
                  }}
                />
              </div>
            )}

            {/* Content - Larger font */}
            <div>
              <h4 className="text-base font-semibold text-gray-700 mb-3">Nội dung:</h4>
              <p className="text-gray-800 whitespace-pre-wrap text-base leading-relaxed">
                {selectedPost.content}
              </p>
            </div>

            {/* Hashtags - Larger */}
            {selectedPost.hashtags && selectedPost.hashtags.length > 0 && (
              <div>
                <h4 className="text-base font-semibold text-gray-700 mb-3">Hashtags:</h4>
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
              </div>
            )}

            {/* Full Content - Larger */}
            {selectedPost.full_content && selectedPost.full_content.trim() && (
              <div>
                <h4 className="text-base font-semibold text-gray-700 mb-3">
                  Nội dung đầy đủ:
                </h4>
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <p className="text-gray-700 whitespace-pre-wrap text-base leading-relaxed">
                    {selectedPost.full_content}
                  </p>
                </div>
              </div>
            )}

            {/* Agent Reasoning */}
            {selectedPost.agent_reasoning && selectedPost.agent_reasoning.trim() && (
              <div>
                <h4 className="text-base font-semibold text-gray-700 mb-3">
                  Lý do của Agent:
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
          <div className="px-6 py-4 border-t border-gray-200">
            <button
              onClick={() => handleDelete(selectedPost.id)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Xóa bài đăng
            </button>
          </div>
        </div>
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
              <h4 className="text-sm font-medium text-gray-700 mb-3">Chọn Page để đăng:</h4>

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

              {/* Selected posts preview */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Bài đăng sẽ được đăng:</h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {selectedPostIds.map(postId => {
                    const post = posts.find(p => p.id === postId);
                    if (!post) return null;
                    return (
                      <div key={postId} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                        {post.image_url ? (
                          <img
                            src={`${getApiUrl()}${post.image_url}`}
                            alt=""
                            className="w-10 h-10 rounded object-cover"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded bg-gray-200 flex items-center justify-center">
                            <ImageIcon className="w-5 h-5 text-gray-400" />
                          </div>
                        )}
                        <p className="text-xs text-gray-600 line-clamp-2 flex-1">{post.content}</p>
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
                <button
                  onClick={handlePublish}
                  disabled={selectedPages.length === 0 || isPublishing}
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
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

AgentPostsGallery.displayName = 'AgentPostsGallery';
