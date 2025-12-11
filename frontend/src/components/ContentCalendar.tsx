'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { ChevronLeft, ChevronRight, AlertCircle, Trash2, Eye, Sparkles, Calendar as CalendarIcon, ChevronDown, ChevronUp } from 'lucide-react';

interface Post {
  id: string;
  content: string;
  scheduledDate: Date;
  status: 'published' | 'scheduled' | 'draft' | 'failed';
  page: string;
  likes?: number;
  shares?: number;
  comments?: number;
  mediaUrl?: string;
  fullPost?: any; // Full scheduled post data from database
}

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

export function ContentCalendar() {
  const { tokens } = useAuth();

  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [view, setView] = useState<'calendar' | 'list'>('calendar');

  // AI Schedule Generator states
  const [showAIGenerator, setShowAIGenerator] = useState(false);
  const [businessType, setBusinessType] = useState('');
  const [goals, setGoals] = useState('');
  const [startDate, setStartDate] = useState('');
  const [duration, setDuration] = useState<'1_week' | '2_weeks' | '1_month'>('1_week');
  const [postsPerDay, setPostsPerDay] = useState(2);
  const [isGeneratingSchedule, setIsGeneratingSchedule] = useState(false);
  const [generatedSchedule, setGeneratedSchedule] = useState<any>(null);
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);
  const [scheduleStatus, setScheduleStatus] = useState<{type: 'success' | 'error' | null, message: string}>({type: null, message: ''});
  const [currentStep, setCurrentStep] = useState<{step: string, stepName: string, message: string} | null>(null);

  // Scheduled posts from database
  const [scheduledPosts, setScheduledPosts] = useState<any[]>([]);
  const [loadingScheduledPosts, setLoadingScheduledPosts] = useState(false);

  // Posting schedules
  const [postingSchedules, setPostingSchedules] = useState<any[]>([]);
  const [showSchedulesPanel, setShowSchedulesPanel] = useState(false);

  // Pages data
  const [pages, setPages] = useState<Array<{id: string, name: string, avatar: string}>>([]);
  const [loadingPages, setLoadingPages] = useState(true);

  // Fetch pages
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

  // Fetch scheduled posts from database
  const fetchScheduledPosts = async () => {
    if (!tokens) return;

    setLoadingScheduledPosts(true);
    try {
      const response = await fetch(`${getApiUrl()}/api/ai/scheduled-posts`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setScheduledPosts(data);
      }
    } catch (error) {
      console.error('Error fetching scheduled posts:', error);
    } finally {
      setLoadingScheduledPosts(false);
    }
  };

  // Fetch posting schedules from database
  const fetchSchedules = async () => {
    if (!tokens) return;

    try {
      const response = await fetch(`${getApiUrl()}/api/ai/schedules`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setPostingSchedules(data);
      }
    } catch (error) {
      console.error('Error fetching schedules:', error);
    }
  };

  // Fetch scheduled posts on mount
  useEffect(() => {
    fetchScheduledPosts();
    fetchSchedules();
  }, [tokens]);

  // Generate schedule handler with streaming progress
  const handleGenerateSchedule = async () => {
    if (!businessType.trim() || !goals.trim() || !startDate) {
      setScheduleStatus({type: 'error', message: 'Vui lòng điền đầy đủ thông tin'});
      return;
    }

    setIsGeneratingSchedule(true);
    setScheduleStatus({type: null, message: ''});
    setGeneratedSchedule(null);
    setCurrentStep(null);

    try {
      const formData = new FormData();
      formData.append('business_type', businessType);
      formData.append('goals', goals);
      formData.append('start_date', startDate);
      formData.append('duration', duration);
      formData.append('posts_per_day', postsPerDay.toString());
      formData.append('language', 'vi');

      // Use streaming endpoint for progress updates
      const response = await fetch(`${getApiUrl()}/api/ai/schedule/stream`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to generate schedule');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Cannot read response stream');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process SSE events
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));

              if (event.type === 'progress') {
                setCurrentStep({
                  step: event.step,
                  stepName: event.step_name,
                  message: event.message
                });
              } else if (event.type === 'done') {
                setCurrentStep({
                  step: event.step,
                  stepName: event.step_name,
                  message: event.message
                });
                setGeneratedSchedule(event.data);
                setScheduleStatus({type: 'success', message: 'Đã tạo lịch đăng bài thành công!'});
              } else if (event.type === 'error') {
                setScheduleStatus({type: 'error', message: event.message});
              }
            } catch (e) {
              console.error('Error parsing SSE event:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Schedule generation error:', error);
      setScheduleStatus({type: 'error', message: 'Có lỗi xảy ra khi tạo lịch đăng bài'});
    } finally {
      setIsGeneratingSchedule(false);
      setCurrentStep(null);
    }
  };

  // Save schedule to database handler
  const handleSaveSchedule = async () => {
    if (!tokens || !generatedSchedule?.posts) {
      setScheduleStatus({type: 'error', message: 'Không có lịch đăng để lưu'});
      return;
    }

    setIsSavingSchedule(true);
    setScheduleStatus({type: null, message: ''});

    try {
      const response = await fetch(`${getApiUrl()}/api/ai/scheduled-posts/save`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          posts: generatedSchedule.posts,
          business_type: businessType,
          goals: goals,
          start_date: startDate,
          duration: duration,
          posts_per_day: postsPerDay,
          strategy_overview: generatedSchedule.schedule_summary?.strategy_overview || '',
          hashtag_suggestions: generatedSchedule.hashtag_suggestions || [],
          engagement_tips: generatedSchedule.engagement_tips || ''
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save schedule');
      }

      const data = await response.json();
      setScheduleStatus({
        type: 'success',
        message: `Đã lưu thành công ${data.saved_count} bài đăng vào lịch (ID: ${data.schedule_id})!`
      });

      // Refresh scheduled posts
      await fetchScheduledPosts();

      // Clear form
      setGeneratedSchedule(null);
      setBusinessType('');
      setGoals('');
      setStartDate('');
    } catch (error) {
      console.error('Save schedule error:', error);
      setScheduleStatus({
        type: 'error',
        message: error instanceof Error ? error.message : 'Đã xảy ra lỗi khi lưu lịch đăng'
      });
    } finally {
      setIsSavingSchedule(false);
    }
  };

  // Delete scheduled post
  const handleDeleteScheduledPost = async (postId: number) => {
    if (!tokens) return;

    try {
      const response = await fetch(`${getApiUrl()}/api/ai/scheduled-posts/${postId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (response.ok) {
        await fetchScheduledPosts();
        await fetchSchedules();
      }
    } catch (error) {
      console.error('Error deleting post:', error);
    }
  };

  // Delete entire schedule (deletes all posts in the schedule)
  const handleDeleteSchedule = async (scheduleId: number) => {
    if (!tokens) return;

    if (!confirm('Bạn có chắc muốn xóa toàn bộ lịch đăng này? Tất cả bài đăng trong lịch trình sẽ bị xóa.')) {
      return;
    }

    try {
      const response = await fetch(`${getApiUrl()}/api/ai/schedules/${scheduleId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setScheduleStatus({
          type: 'success',
          message: `Đã xóa lịch trình và ${data.deleted_posts_count} bài đăng!`
        });
        await fetchScheduledPosts();
        await fetchSchedules();
      }
    } catch (error) {
      console.error('Error deleting schedule:', error);
      setScheduleStatus({
        type: 'error',
        message: 'Có lỗi xảy ra khi xóa lịch trình'
      });
    }
  };

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();
    
    return { daysInMonth, startingDayOfWeek };
  };

  const { daysInMonth, startingDayOfWeek } = getDaysInMonth(currentDate);

  const getPostsForDay = (day: number) => {
    // Get scheduled posts from database
    const scheduledPostsForDay = scheduledPosts
      .filter((post) => {
        const postDate = new Date(post.schedule_date);
        return (
          postDate.getDate() === day &&
          postDate.getMonth() === currentDate.getMonth() &&
          postDate.getFullYear() === currentDate.getFullYear()
        );
      })
      .map((post) => ({
        id: `scheduled-${post.id}`,
        content: post.title || post.hook || 'Bài đăng đã lên lịch',
        scheduledDate: new Date(`${post.schedule_date}T${post.schedule_time}`),
        status: post.status as 'published' | 'scheduled' | 'draft' | 'failed',
        page: post.business_type,
        fullPost: post
      }));

    return scheduledPostsForDay;
  };

  const previousMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const getStatusBadge = (status: Post['status']) => {
    const styles = {
      published: 'bg-green-100 text-green-700',
      scheduled: 'bg-blue-100 text-blue-700',
      draft: 'bg-gray-100 text-gray-700',
      failed: 'bg-red-100 text-red-700',
    };

    const labels = {
      published: 'Đã đăng',
      scheduled: 'Đã lên lịch',
      draft: 'Nháp',
      failed: 'Lỗi',
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  const monthNames = [
    'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
    'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
  ];

  const dayNames = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];

  return (
    <div className="p-8">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-gray-900 mb-2">Lịch đăng bài</h2>
          <p className="text-gray-600">Quản lý bài viết đã đăng và lên lịch</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setView('calendar')}
            className={`px-4 py-2 rounded-lg ${
              view === 'calendar' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            Lịch
          </button>
          <button
            onClick={() => setView('list')}
            className={`px-4 py-2 rounded-lg ${
              view === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            Danh sách
          </button>
        </div>
      </div>

      {/* AI Schedule Generator Section */}
      <div className="mb-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border-2 border-purple-200">
        <button
          onClick={() => setShowAIGenerator(!showAIGenerator)}
          className="w-full p-6 flex items-center justify-between hover:bg-purple-50/50 transition-colors rounded-lg"
        >
          <div className="flex items-center gap-3">
            <Sparkles className="w-6 h-6 text-purple-600" />
            <div className="text-left">
              <h3 className="text-gray-900">AI Schedule Generator</h3>
              <p className="text-sm text-gray-600">Tạo lịch đăng bài tự động với AI (1 tuần, 2 tuần, hoặc 1 tháng)</p>
            </div>
          </div>
          {showAIGenerator ? (
            <ChevronUp className="w-5 h-5 text-purple-600" />
          ) : (
            <ChevronDown className="w-5 h-5 text-purple-600" />
          )}
        </button>

        {showAIGenerator && (
          <div className="p-6 pt-0 border-t border-purple-200">
            {!generatedSchedule ? (
              /* Schedule Generator Form */
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Business Type */}
                  <div>
                    <label className="block text-sm text-gray-700 mb-2">Loại hình kinh doanh</label>
                    <input
                      type="text"
                      value={businessType}
                      onChange={(e) => setBusinessType(e.target.value)}
                      placeholder="VD: Shop thời trang, Nhà hàng, Gym..."
                      className="w-full px-4 py-2 border-2 border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>

                  {/* Start Date */}
                  <div>
                    <label className="block text-sm text-gray-700 mb-2">Ngày bắt đầu</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full px-4 py-2 border-2 border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>

                {/* Goals */}
                <div>
                  <label className="block text-sm text-gray-700 mb-2">Mục tiêu marketing</label>
                  <textarea
                    value={goals}
                    onChange={(e) => setGoals(e.target.value)}
                    placeholder="VD: Tăng nhận diện thương hiệu, thu hút khách hàng mới, tăng doanh số bán hàng..."
                    className="w-full h-20 px-4 py-2 border-2 border-purple-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Duration */}
                  <div>
                    <label className="block text-sm text-gray-700 mb-2">Thời lượng</label>
                    <select
                      value={duration}
                      onChange={(e) => setDuration(e.target.value as typeof duration)}
                      className="w-full px-4 py-2 border-2 border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="1_week">1 tuần</option>
                      <option value="2_weeks">2 tuần</option>
                      <option value="1_month">1 tháng</option>
                    </select>
                  </div>

                  {/* Posts Per Day */}
                  <div>
                    <label className="block text-sm text-gray-700 mb-2">Số bài/ngày</label>
                    <input
                      type="number"
                      min="1"
                      max="5"
                      value={postsPerDay}
                      onChange={(e) => setPostsPerDay(parseInt(e.target.value))}
                      className="w-full px-4 py-2 border-2 border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>

                {/* Status Message */}
                {scheduleStatus.type && (
                  <div className={`p-3 rounded-lg text-sm ${
                    scheduleStatus.type === 'success'
                      ? 'bg-green-50 border border-green-200 text-green-700'
                      : 'bg-red-50 border border-red-200 text-red-700'
                  }`}>
                    {scheduleStatus.message}
                  </div>
                )}

                {/* Progress Steps Display */}
                {isGeneratingSchedule && currentStep && (
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                      <div>
                        <div className="font-medium text-purple-700">{currentStep.stepName}</div>
                        <div className="text-sm text-purple-600">{currentStep.message}</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Generate Button */}
                <button
                  onClick={handleGenerateSchedule}
                  disabled={!businessType.trim() || !goals.trim() || !startDate || isGeneratingSchedule}
                  className="w-full px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
                >
                  {isGeneratingSchedule ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      {currentStep ? currentStep.stepName : 'Đang tạo lịch đăng bài...'}
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Tạo lịch đăng bài với AI
                    </>
                  )}
                </button>
              </div>
            ) : (
              /* Schedule Preview */
              <div className="space-y-4">
                {/* Summary */}
                <div className="bg-white rounded-lg border-2 border-purple-200 p-4">
                  <h4 className="text-gray-900 mb-2">Tổng quan lịch đăng</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div>
                      <span className="text-gray-600">Loại hình:</span>
                      <p className="text-gray-900 font-medium">{generatedSchedule.schedule_summary?.business_type}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Thời lượng:</span>
                      <p className="text-gray-900 font-medium">{generatedSchedule.schedule_summary?.duration}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Tổng số bài:</span>
                      <p className="text-gray-900 font-medium">{generatedSchedule.schedule_summary?.total_posts}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Model:</span>
                      <p className="text-gray-900 font-medium">{generatedSchedule.model}</p>
                    </div>
                  </div>
                  {generatedSchedule.schedule_summary?.strategy_overview && (
                    <p className="text-sm text-gray-700 mt-3 p-3 bg-purple-50 rounded-lg">
                      {generatedSchedule.schedule_summary.strategy_overview}
                    </p>
                  )}
                </div>

                {/* Posts List */}
                <div className="bg-white rounded-lg border-2 border-purple-200 p-4 max-h-96 overflow-y-auto">
                  <h4 className="text-gray-900 mb-3">Chi tiết các bài đăng ({generatedSchedule.posts?.length})</h4>
                  <div className="space-y-3">
                    {generatedSchedule.posts?.map((post: any, index: number) => (
                      <div key={index} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <h5 className="text-sm text-gray-900 font-medium">{post.title}</h5>
                            <div className="flex gap-2 mt-1 text-xs text-gray-600">
                              <span>{post.date}</span>
                              <span>•</span>
                              <span>{post.time}</span>
                              <span>•</span>
                              <span>{post.day_of_week}</span>
                            </div>
                          </div>
                          <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                            {post.content_type}
                          </span>
                        </div>
                        <div className="text-xs text-gray-700 space-y-1">
                          <p><strong>Hook:</strong> {post.hook}</p>
                          <p className="line-clamp-2"><strong>Body:</strong> {post.body}</p>
                          <p><strong>CTA:</strong> {post.cta}</p>
                          {post.hashtags && (
                            <p className="text-purple-600">{post.hashtags.join(' ')}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={() => setGeneratedSchedule(null)}
                    className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Tạo lịch mới
                  </button>
                  <button
                    onClick={handleSaveSchedule}
                    disabled={isSavingSchedule}
                    className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
                  >
                    {isSavingSchedule ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Đang lưu...
                      </>
                    ) : (
                      <>
                        <CalendarIcon className="w-5 h-5" />
                        Thêm vào lịch đăng
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Schedules Management Panel */}
      {postingSchedules.length > 0 && (
        <div className="mb-6 bg-white rounded-lg border-2 border-gray-200">
          <button
            onClick={() => setShowSchedulesPanel(!showSchedulesPanel)}
            className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors rounded-lg"
          >
            <div className="flex items-center gap-3">
              <CalendarIcon className="w-6 h-6 text-blue-600" />
              <div className="text-left">
                <h3 className="text-gray-900">Quản lý Lịch trình ({postingSchedules.length})</h3>
                <p className="text-sm text-gray-600">Xem và xóa các lịch đăng bài đã tạo</p>
              </div>
            </div>
            {showSchedulesPanel ? (
              <ChevronUp className="w-5 h-5 text-blue-600" />
            ) : (
              <ChevronDown className="w-5 h-5 text-blue-600" />
            )}
          </button>

          {showSchedulesPanel && (
            <div className="p-6 pt-0 border-t border-gray-200">
              <div className="space-y-3">
                {postingSchedules.map((schedule) => (
                  <div key={schedule.id} className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="text-gray-900 font-medium">{schedule.business_type}</h4>
                        <p className="text-sm text-gray-600 mt-1">{schedule.goals}</p>
                        <div className="flex gap-4 mt-2 text-xs text-gray-500">
                          <span>📅 {schedule.start_date}</span>
                          <span>⏱️ {schedule.duration.replace('_', ' ')}</span>
                          <span>📝 {schedule.posts_count}/{schedule.total_posts} bài</span>
                          <span>🕒 {schedule.posts_per_day} bài/ngày</span>
                        </div>
                        {schedule.strategy_overview && (
                          <p className="text-xs text-gray-600 mt-2 italic">"{schedule.strategy_overview}"</p>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteSchedule(schedule.id)}
                        className="ml-4 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 flex items-center gap-2 text-sm transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                        Xóa lịch trình
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {view === 'calendar' ? (
        <>
          {/* Calendar header */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <div className="flex justify-between items-center mb-6">
              <button
                onClick={previousMonth}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <h3 className="text-gray-900">
                {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
              </h3>
              <button
                onClick={nextMonth}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>

            {/* Calendar grid */}
            <div className="grid grid-cols-7 gap-2">
              {dayNames.map((day) => (
                <div key={day} className="text-center text-sm text-gray-600 py-2">
                  {day}
                </div>
              ))}
              
              {Array.from({ length: startingDayOfWeek }).map((_, index) => (
                <div key={`empty-${index}`} className="aspect-square" />
              ))}
              
              {Array.from({ length: daysInMonth }).map((_, index) => {
                const day = index + 1;
                const posts = getPostsForDay(day);
                const today = new Date();
                const isToday =
                  day === today.getDate() &&
                  currentDate.getMonth() === today.getMonth() &&
                  currentDate.getFullYear() === today.getFullYear();

                return (
                  <div
                    key={day}
                    className={`aspect-square border rounded-lg p-2 ${
                      isToday ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'
                    } hover:shadow-md transition-shadow`}
                  >
                    <div className="text-sm text-gray-700 mb-1">{day}</div>
                    <div className="space-y-1">
                      {posts.slice(0, 3).map((post) => (
                        <button
                          key={post.id}
                          onClick={() => setSelectedPost(post)}
                          className="w-full text-xs text-left p-1 rounded truncate hover:bg-gray-100"
                          style={{
                            backgroundColor:
                              post.status === 'published' ? '#dcfce7' :
                              post.status === 'scheduled' ? '#dbeafe' :
                              post.status === 'draft' ? '#f3f4f6' :
                              '#fee2e2',
                          }}
                        >
                          {post.content}
                        </button>
                      ))}
                      {posts.length > 3 && (
                        <div className="text-xs text-gray-500 text-center">
                          +{posts.length - 3} bài
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      ) : (
        /* List view */
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm text-gray-600">Nội dung</th>
                  <th className="px-6 py-3 text-left text-sm text-gray-600">Page / Loại hình</th>
                  <th className="px-6 py-3 text-left text-sm text-gray-600">Thời gian</th>
                  <th className="px-6 py-3 text-left text-sm text-gray-600">Trạng thái</th>
                  <th className="px-6 py-3 text-left text-sm text-gray-600">Tương tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {/* Scheduled posts from database */}
                {scheduledPosts.map((post) => {
                  const scheduledDate = new Date(`${post.schedule_date}T${post.schedule_time}`);
                  const postData = {
                    id: `scheduled-${post.id}`,
                    content: post.title || post.hook || 'Bài đăng đã lên lịch',
                    scheduledDate,
                    status: post.status as 'published' | 'scheduled' | 'draft' | 'failed',
                    page: post.business_type,
                    fullPost: post
                  };

                  return (
                    <tr
                      key={postData.id}
                      className="hover:bg-gray-50 bg-purple-50/30 cursor-pointer"
                      onClick={() => setSelectedPost(postData)}
                    >
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900 max-w-xs">
                          <div className="font-medium truncate">{post.title}</div>
                          <div className="text-xs text-gray-600 truncate">{post.hook}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-700">{post.business_type}</div>
                        <div className="text-xs text-gray-500">{post.content_type}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-700">
                          {scheduledDate.toLocaleDateString('vi-VN')}
                          <br />
                          {scheduledDate.toLocaleTimeString('vi-VN', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      </td>
                      <td className="px-6 py-4">{getStatusBadge(postData.status)}</td>
                      <td className="px-6 py-4">
                        <div className="text-xs text-purple-600">
                          AI Generated
                        </div>
                      </td>
                    </tr>
                  );
                })}

                {scheduledPosts.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      Chưa có bài đăng nào
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Post detail modal - shown for both calendar and list view */}
      {selectedPost && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-gray-900 mb-2">Chi tiết bài đăng</h3>
                {getStatusBadge(selectedPost.status)}
              </div>
              <button
                onClick={() => setSelectedPost(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              {selectedPost.fullPost ? (
                /* Scheduled post from database */
                <>
                  <div>
                    <label className="text-sm text-gray-600">Tiêu đề</label>
                    <p className="text-gray-900 mt-1 font-medium">{selectedPost.fullPost.title}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Loại nội dung</label>
                      <p className="text-gray-900 mt-1">{selectedPost.fullPost.content_type}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Mục tiêu</label>
                      <p className="text-gray-900 mt-1">{selectedPost.fullPost.goal}</p>
                    </div>
                  </div>

                  <div>
                    <label className="text-sm text-gray-600">Hook (Câu mở đầu)</label>
                    <p className="text-gray-900 mt-1 whitespace-pre-wrap">{selectedPost.fullPost.hook}</p>
                  </div>

                  <div>
                    <label className="text-sm text-gray-600">Nội dung chính</label>
                    <p className="text-gray-900 mt-1 whitespace-pre-wrap">{selectedPost.fullPost.body}</p>
                  </div>

                  <div>
                    <label className="text-sm text-gray-600">Câu hỏi tương tác</label>
                    <p className="text-gray-900 mt-1">{selectedPost.fullPost.engagement}</p>
                  </div>

                  <div>
                    <label className="text-sm text-gray-600">Call to Action</label>
                    <p className="text-gray-900 mt-1">{selectedPost.fullPost.cta}</p>
                  </div>

                  {selectedPost.fullPost.hashtags && selectedPost.fullPost.hashtags.length > 0 && (
                    <div>
                      <label className="text-sm text-gray-600">Hashtags</label>
                      <p className="text-purple-600 mt-1">{selectedPost.fullPost.hashtags.join(' ')}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                    <div>
                      <label className="text-sm text-gray-600">Loại hình</label>
                      <p className="text-gray-900 mt-1">{selectedPost.fullPost.business_type}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Thời gian</label>
                      <p className="text-gray-900 mt-1">
                        {selectedPost.scheduledDate.toLocaleString('vi-VN')}
                      </p>
                    </div>
                  </div>

                  <div className="p-4 bg-gray-50 rounded-lg">
                    <label className="text-sm text-gray-600 mb-2 block">Nội dung đầy đủ:</label>
                    <div className="text-sm text-gray-900 whitespace-pre-wrap">
                      {selectedPost.fullPost.full_content}
                    </div>
                  </div>
                </>
              ) : (
                /* Regular post */
                <>
                  <div>
                    <label className="text-sm text-gray-600">Nội dung</label>
                    <p className="text-gray-900 mt-1">{selectedPost.content}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Page</label>
                      <p className="text-gray-900 mt-1">{selectedPost.page}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Thời gian</label>
                      <p className="text-gray-900 mt-1">
                        {selectedPost.scheduledDate.toLocaleString('vi-VN')}
                      </p>
                    </div>
                  </div>

                  {selectedPost.status === 'published' && (
                    <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
                      <div className="text-center">
                        <div className="text-gray-600 text-sm">Likes</div>
                        <div className="text-gray-900">{selectedPost.likes}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-gray-600 text-sm">Shares</div>
                        <div className="text-gray-900">{selectedPost.shares}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-gray-600 text-sm">Comments</div>
                        <div className="text-gray-900">{selectedPost.comments}</div>
                      </div>
                    </div>
                  )}
                </>
              )}

              {selectedPost.status === 'failed' && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                    <div>
                      <p className="text-red-900">Lỗi đăng bài</p>
                      <p className="text-sm text-red-700 mt-1">
                        Token hết hạn. Vui lòng kết nối lại Page.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-4">
                {selectedPost.fullPost ? (
                  <button
                    onClick={async () => {
                      if (confirm('Bạn có chắc muốn xóa bài đăng này?')) {
                        await handleDeleteScheduledPost(selectedPost.fullPost.id);
                        setSelectedPost(null);
                      }
                    }}
                    className="w-full px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 flex items-center justify-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Xóa bài đăng
                  </button>
                ) : (
                  <>
                    <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2">
                      <Eye className="w-4 h-4" />
                      Xem trên Facebook
                    </button>
                    <button className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 flex items-center gap-2">
                      <Trash2 className="w-4 h-4" />
                      Xóa
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
