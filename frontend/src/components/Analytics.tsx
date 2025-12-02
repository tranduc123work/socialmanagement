'use client';

import { useState, useEffect } from 'react';
import { FileText, CheckCircle, Clock, AlertCircle, Users, Bot, Calendar, Loader2, Facebook, Timer, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

interface GenerationTimeStats {
  avg_seconds: number | null;
  min_seconds: number | null;
  max_seconds: number | null;
  recent_posts: Array<{
    id: number;
    content_preview: string;
    generation_time_seconds: number;
    created_at: string;
  }>;
}

interface DashboardStats {
  social_posts: {
    total: number;
    published: number;
    scheduled: number;
    draft: number;
    failed: number;
  };
  agent_posts: {
    total: number;
    completed: number;
    generating: number;
    failed: number;
    generation_time: GenerationTimeStats;
  };
  connected_accounts: {
    total: number;
    facebook: number;
  };
  scheduled_content: {
    total: number;
    draft: number;
    approved: number;
  };
}

const getApiUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== 'undefined') {
    return `http://${window.location.hostname}:8000`;
  }
  return 'http://localhost:8000';
};

// Format seconds to readable time (e.g., "2m 30s" or "45s")
const formatTime = (seconds: number | null): string => {
  if (seconds === null) return '-';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
};

export function Analytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const tokensStr = localStorage.getItem('tokens');
        const tokens = tokensStr ? JSON.parse(tokensStr) : null;
        const accessToken = tokens?.access_token || '';

        const response = await fetch(`${getApiUrl()}/api/analytics/overview`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch stats');
        }

        const data = await response.json();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  // Prepare pie chart data for social posts
  const socialPostsChartData = stats ? [
    { name: 'Đã đăng', value: stats.social_posts.published, color: '#10b981' },
    { name: 'Chờ đăng', value: stats.social_posts.scheduled, color: '#3b82f6' },
    { name: 'Bản nháp', value: stats.social_posts.draft, color: '#9ca3af' },
    { name: 'Thất bại', value: stats.social_posts.failed, color: '#ef4444' },
  ].filter(item => item.value > 0) : [];

  // Prepare pie chart data for agent posts
  const agentPostsChartData = stats ? [
    { name: 'Hoàn thành', value: stats.agent_posts.completed, color: '#10b981' },
    { name: 'Đang tạo', value: stats.agent_posts.generating, color: '#f59e0b' },
  ].filter(item => item.value > 0) : [];

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <p className="text-gray-600">Đang tải thống kê...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-gray-900 text-2xl font-bold mb-2">Thống kê hệ thống</h2>
        <p className="text-gray-600">Tổng quan về bài đăng và tài khoản</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Social Posts */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <p className="text-gray-600 text-sm mb-1">Bài đăng Platform</p>
          <p className="text-gray-900 text-2xl font-bold">{stats?.social_posts.total || 0}</p>
          <div className="mt-2 flex gap-2 text-xs">
            <span className="text-green-600">{stats?.social_posts.published || 0} đã đăng</span>
            <span className="text-gray-400">|</span>
            <span className="text-blue-600">{stats?.social_posts.scheduled || 0} chờ</span>
          </div>
        </div>

        {/* Agent Posts */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
              <Bot className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <p className="text-gray-600 text-sm mb-1">Bài do Agent tạo</p>
          <p className="text-gray-900 text-2xl font-bold">{stats?.agent_posts.total || 0}</p>
          <div className="mt-2 flex gap-2 text-xs">
            <span className="text-green-600">{stats?.agent_posts.completed || 0} hoàn thành</span>
            <span className="text-gray-400">|</span>
            <span className="text-yellow-600">{stats?.agent_posts.generating || 0} đang tạo</span>
          </div>
        </div>

        {/* Connected Accounts */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
              <Users className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <p className="text-gray-600 text-sm mb-1">Tài khoản kết nối</p>
          <p className="text-gray-900 text-2xl font-bold">{stats?.connected_accounts.total || 0}</p>
          <div className="mt-2 flex gap-2 text-xs">
            <Facebook className="w-4 h-4 text-blue-600" />
            <span className="text-blue-600">{stats?.connected_accounts.facebook || 0} Facebook</span>
          </div>
        </div>

        {/* Scheduled Content */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center">
              <Calendar className="w-6 h-6 text-orange-600" />
            </div>
          </div>
          <p className="text-gray-600 text-sm mb-1">Lịch đăng</p>
          <p className="text-gray-900 text-2xl font-bold">{stats?.scheduled_content.total || 0}</p>
          <div className="mt-2 flex gap-2 text-xs">
            <span className="text-gray-600">{stats?.scheduled_content.draft || 0} nháp</span>
            <span className="text-gray-400">|</span>
            <span className="text-green-600">{stats?.scheduled_content.approved || 0} đã duyệt</span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Social Posts Distribution */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-gray-900 font-semibold mb-6">Phân bố bài đăng Platform</h3>
          {socialPostsChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={socialPostsChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {socialPostsChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-500">
              Chưa có bài đăng nào
            </div>
          )}
        </div>

        {/* Agent Posts Distribution */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-gray-900 font-semibold mb-6">Bài đăng do Agent tạo</h3>
          {agentPostsChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={agentPostsChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {agentPostsChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-500">
              Chưa có bài đăng nào do Agent tạo
            </div>
          )}
        </div>
      </div>

      {/* Agent Generation Time Stats */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <div className="flex items-center gap-3 mb-6">
          <Timer className="w-6 h-6 text-purple-600" />
          <h3 className="text-gray-900 font-semibold">Thời gian tạo bài của Agent</h3>
        </div>

        {stats?.agent_posts?.generation_time?.avg_seconds != null ? (
          <>
            {/* Time Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="flex items-center gap-3 p-4 bg-purple-50 rounded-lg">
                <Activity className="w-8 h-8 text-purple-600" />
                <div>
                  <p className="text-2xl font-bold text-purple-700">
                    {formatTime(stats.agent_posts.generation_time.avg_seconds ?? null)}
                  </p>
                  <p className="text-sm text-purple-600">Trung bình</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
                <TrendingDown className="w-8 h-8 text-green-600" />
                <div>
                  <p className="text-2xl font-bold text-green-700">
                    {formatTime(stats.agent_posts.generation_time.min_seconds ?? null)}
                  </p>
                  <p className="text-sm text-green-600">Nhanh nhất</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-orange-50 rounded-lg">
                <TrendingUp className="w-8 h-8 text-orange-600" />
                <div>
                  <p className="text-2xl font-bold text-orange-700">
                    {formatTime(stats.agent_posts.generation_time.max_seconds ?? null)}
                  </p>
                  <p className="text-sm text-orange-600">Chậm nhất</p>
                </div>
              </div>
            </div>

            {/* Recent Posts Generation Time Chart */}
            {(stats.agent_posts.generation_time.recent_posts?.length ?? 0) > 0 && (
              <div>
                <h4 className="text-gray-700 font-medium mb-4">5 bài gần nhất</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={stats.agent_posts.generation_time.recent_posts}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="id"
                      tickFormatter={(id) => `#${id}`}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis
                      tickFormatter={(value) => formatTime(value)}
                      tick={{ fontSize: 12 }}
                    />
                    <Tooltip
                      formatter={(value: number) => [formatTime(value), 'Thời gian']}
                      labelFormatter={(id) => `Bài #${id}`}
                    />
                    <Bar
                      dataKey="generation_time_seconds"
                      fill="#8b5cf6"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>

                {/* Recent Posts Table */}
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 px-3 text-gray-600">ID</th>
                        <th className="text-left py-2 px-3 text-gray-600">Nội dung</th>
                        <th className="text-right py-2 px-3 text-gray-600">Thời gian tạo</th>
                        <th className="text-right py-2 px-3 text-gray-600">Ngày tạo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.agent_posts.generation_time.recent_posts.map((post) => (
                        <tr key={post.id} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-2 px-3 text-gray-700">#{post.id}</td>
                          <td className="py-2 px-3 text-gray-700 max-w-xs truncate">{post.content_preview}</td>
                          <td className="py-2 px-3 text-right">
                            <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                              <Clock className="w-3 h-3" />
                              {formatTime(post.generation_time_seconds)}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right text-gray-500">
                            {new Date(post.created_at).toLocaleDateString('vi-VN')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="h-[150px] flex items-center justify-center text-gray-500">
            Chưa có dữ liệu thời gian tạo bài. Agent cần tạo ít nhất 1 bài hoàn chỉnh.
          </div>
        )}
      </div>

      {/* Status Summary */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-gray-900 font-semibold mb-6">Chi tiết trạng thái</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
            <CheckCircle className="w-8 h-8 text-green-600" />
            <div>
              <p className="text-2xl font-bold text-green-700">{stats?.social_posts.published || 0}</p>
              <p className="text-sm text-green-600">Đã đăng</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg">
            <Clock className="w-8 h-8 text-blue-600" />
            <div>
              <p className="text-2xl font-bold text-blue-700">{stats?.social_posts.scheduled || 0}</p>
              <p className="text-sm text-blue-600">Chờ đăng</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
            <FileText className="w-8 h-8 text-gray-600" />
            <div>
              <p className="text-2xl font-bold text-gray-700">{stats?.social_posts.draft || 0}</p>
              <p className="text-sm text-gray-600">Bản nháp</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg">
            <AlertCircle className="w-8 h-8 text-red-600" />
            <div>
              <p className="text-2xl font-bold text-red-700">{stats?.social_posts.failed || 0}</p>
              <p className="text-sm text-red-600">Thất bại</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
