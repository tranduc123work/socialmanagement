'use client';

import { useState } from 'react';
import { FileText, Calendar, Image, Users, BarChart3, LogOut, Bot, Settings } from 'lucide-react';
import { PostComposer } from './PostComposer';
import { ContentCalendar } from './ContentCalendar';
import { MediaLibrary } from './MediaLibrary';
import { AccountsManager } from './AccountsManager';
import { Analytics } from './Analytics';
import { AgentDashboard } from './AgentDashboard';
import { PageSettings } from './PageSettings';
import { useAuth } from '@/contexts/AuthContext';

type Tab = 'composer' | 'calendar' | 'media' | 'accounts' | 'page-settings' | 'analytics' | 'agent';

const tabs = [
  { id: 'composer' as Tab, label: 'Soạn bài', icon: FileText, component: PostComposer },
  { id: 'calendar' as Tab, label: 'Lịch đăng', icon: Calendar, component: ContentCalendar },
  { id: 'media' as Tab, label: 'Thư viện', icon: Image, component: MediaLibrary },
  { id: 'accounts' as Tab, label: 'Tài khoản', icon: Users, component: AccountsManager },
  { id: 'page-settings' as Tab, label: 'Cài đặt trang', icon: Settings, component: PageSettings },
  { id: 'analytics' as Tab, label: 'Thống kê', icon: BarChart3, component: Analytics },
  { id: 'agent' as Tab, label: 'AI Agent', icon: Bot, component: AgentDashboard },
];

export function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('composer');
  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || PostComposer;
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-blue-600 text-xl font-bold">Social Manager</h1>
          <p className="text-gray-500 text-sm mt-1">Quản lý mạng xã hội</p>
        </div>

        <nav className="flex-1 p-4">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                activeTab === id ? 'bg-blue-50 text-blue-600' : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-sm font-medium">
              {user?.username?.substring(0, 2).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.username || 'User'}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email || ''}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              title="Đăng xuất"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 min-h-0 h-full overflow-y-auto">
        <ActiveComponent />
      </div>
    </div>
  );
}
