'use client';

import { useState } from 'react';
import { TrendingUp, Heart, Share2, MessageCircle, Eye, Calendar } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const engagementData = [
  { date: '15/11', likes: 234, shares: 45, comments: 18 },
  { date: '16/11', likes: 189, shares: 32, comments: 12 },
  { date: '17/11', likes: 421, shares: 89, comments: 34 },
  { date: '18/11', likes: 567, shares: 123, comments: 89 },
  { date: '19/11', likes: 312, shares: 67, comments: 23 },
  { date: '20/11', likes: 445, shares: 98, comments: 45 },
];

const postTypeData = [
  { name: 'Photo', value: 45, color: '#3b82f6' },
  { name: 'Video', value: 25, color: '#8b5cf6' },
  { name: 'Text', value: 20, color: '#10b981' },
  { name: 'Link', value: 10, color: '#f59e0b' },
];

const bestTimeData = [
  { hour: '6h', posts: 2 },
  { hour: '9h', posts: 8 },
  { hour: '12h', posts: 15 },
  { hour: '15h', posts: 12 },
  { hour: '18h', posts: 20 },
  { hour: '21h', posts: 18 },
  { hour: '24h', posts: 5 },
];

const topPosts = [
  {
    id: '1',
    content: 'Mẹo marketing hiệu quả cho doanh nghiệp nhỏ',
    likes: 567,
    shares: 123,
    comments: 89,
    reach: 12450,
    engagement: 6.2,
    date: '18/11/2025',
  },
  {
    id: '2',
    content: 'Sale 50% toàn bộ sản phẩm - Giảm giá sốc!',
    likes: 421,
    shares: 89,
    comments: 34,
    reach: 8920,
    engagement: 5.8,
    date: '17/11/2025',
  },
  {
    id: '3',
    content: 'Chào mừng đến với tháng mới! 🎉',
    likes: 234,
    shares: 45,
    comments: 18,
    reach: 5670,
    engagement: 5.2,
    date: '15/11/2025',
  },
];

export function Analytics() {
  const [timeRange, setTimeRange] = useState<'7days' | '30days' | '90days'>('7days');
  const [selectedPage, setSelectedPage] = useState('all');

  const mockPages = [
    { id: 'all', name: 'Tất cả Pages' },
    { id: '1', name: 'Page Kinh Doanh Online' },
    { id: '2', name: 'Shop Thời Trang ABC' },
    { id: '3', name: 'Cộng đồng Marketing' },
  ];

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-gray-900 mb-2">Thống kê & Phân tích</h2>
        <p className="text-gray-600">Theo dõi hiệu suất bài đăng</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6 flex gap-4 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm text-gray-700 mb-2">Page</label>
          <select
            value={selectedPage}
            onChange={(e) => setSelectedPage(e.target.value)}
            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {mockPages.map((page) => (
              <option key={page.id} value={page.id}>
                {page.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm text-gray-700 mb-2">Khoảng thời gian</label>
          <div className="flex gap-2">
            {[
              { value: '7days' as const, label: '7 ngày' },
              { value: '30days' as const, label: '30 ngày' },
              { value: '90days' as const, label: '90 ngày' },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => setTimeRange(option.value)}
                className={`px-4 py-2 rounded-lg ${
                  timeRange === option.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
              <Heart className="w-6 h-6 text-red-600" />
            </div>
            <span className="text-green-600 text-sm flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              +12.5%
            </span>
          </div>
          <p className="text-gray-600 text-sm mb-1">Tổng Likes</p>
          <p className="text-gray-900">2,168</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
              <Share2 className="w-6 h-6 text-blue-600" />
            </div>
            <span className="text-green-600 text-sm flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              +8.3%
            </span>
          </div>
          <p className="text-gray-600 text-sm mb-1">Tổng Shares</p>
          <p className="text-gray-900">454</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
              <MessageCircle className="w-6 h-6 text-green-600" />
            </div>
            <span className="text-green-600 text-sm flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              +15.7%
            </span>
          </div>
          <p className="text-gray-600 text-sm mb-1">Tổng Comments</p>
          <p className="text-gray-900">221</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
              <Eye className="w-6 h-6 text-purple-600" />
            </div>
            <span className="text-green-600 text-sm flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              +22.1%
            </span>
          </div>
          <p className="text-gray-600 text-sm mb-1">Tổng Reach</p>
          <p className="text-gray-900">45,320</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Engagement over time */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-gray-900 mb-6">Tương tác theo thời gian</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={engagementData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="likes" stroke="#ef4444" strokeWidth={2} name="Likes" />
              <Line type="monotone" dataKey="shares" stroke="#3b82f6" strokeWidth={2} name="Shares" />
              <Line type="monotone" dataKey="comments" stroke="#10b981" strokeWidth={2} name="Comments" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Post type distribution */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-gray-900 mb-6">Phân bố loại bài đăng</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={postTypeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {postTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Best time to post */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <h3 className="text-gray-900 mb-6">Thời điểm đăng tốt nhất</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={bestTimeData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="hour" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
            />
            <Bar dataKey="posts" fill="#8b5cf6" radius={[8, 8, 0, 0]} name="Số bài đăng hiệu quả" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top performing posts */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-gray-900">Top bài đăng hiệu quả nhất</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm text-gray-600">Nội dung</th>
                <th className="px-6 py-3 text-left text-sm text-gray-600">Ngày đăng</th>
                <th className="px-6 py-3 text-left text-sm text-gray-600">Likes</th>
                <th className="px-6 py-3 text-left text-sm text-gray-600">Shares</th>
                <th className="px-6 py-3 text-left text-sm text-gray-600">Comments</th>
                <th className="px-6 py-3 text-left text-sm text-gray-600">Reach</th>
                <th className="px-6 py-3 text-left text-sm text-gray-600">Engagement</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {topPosts.map((post) => (
                <tr key={post.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="text-sm text-gray-900 max-w-md">{post.content}</p>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-sm text-gray-700">{post.date}</p>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Heart className="w-4 h-4 text-red-500" />
                      <span className="text-sm text-gray-900">{post.likes}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Share2 className="w-4 h-4 text-blue-500" />
                      <span className="text-sm text-gray-900">{post.shares}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <MessageCircle className="w-4 h-4 text-green-500" />
                      <span className="text-sm text-gray-900">{post.comments}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Eye className="w-4 h-4 text-purple-500" />
                      <span className="text-sm text-gray-900">{post.reach.toLocaleString()}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                      {post.engagement}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
