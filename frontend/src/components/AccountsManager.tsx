'use client';

import { useState, useEffect } from 'react';
import {
  Facebook,
  Instagram,
  MessageCircle,
  Music,
  Youtube,
  Twitter,
  AtSign,
  Plus,
  Trash2,
  RefreshCw,
  Check,
  AlertCircle,
  ExternalLink,
  Settings
} from 'lucide-react';
import { ImageWithFallback } from './figma/ImageWithFallback';
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

interface SocialAccount {
  id: number;
  platform: string;
  platform_account_id: string;
  name: string;
  username?: string;
  profile_picture_url?: string;
  category?: string;
  is_active: boolean;
  is_token_expired: boolean;
  created_at: string;
}

interface PlatformInfo {
  id: string;
  name: string;
  icon: string;
  connected_accounts: number;
  supported_features: string[];
}

const platformIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  facebook: Facebook,
  instagram: Instagram,
  zalo: MessageCircle,
  tiktok: Music,
  youtube: Youtube,
  twitter: Twitter,
  threads: AtSign,
};

const platformColors: Record<string, string> = {
  facebook: 'bg-blue-600',
  instagram: 'bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500',
  zalo: 'bg-blue-500',
  tiktok: 'bg-black',
  youtube: 'bg-red-600',
  twitter: 'bg-sky-500',
  threads: 'bg-black',
};

export function AccountsManager() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);

  const { tokens, isAuthenticated } = useAuth();
  const API_BASE_URL = getApiUrl();

  useEffect(() => {
    fetchData();
  }, [tokens]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      // Fetch platforms info (no auth needed)
      const platformsRes = await fetch(`${API_BASE_URL}/api/platforms/info`);
      if (platformsRes.ok) {
        const platformsData = await platformsRes.json();
        setPlatforms(platformsData);
      }

      // Fetch connected accounts (requires auth)
      if (tokens) {
        const accountsRes = await fetch(`${API_BASE_URL}/api/platforms/accounts`, {
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`
          }
        });
        if (accountsRes.ok) {
          const accountsData = await accountsRes.json();
          setAccounts(accountsData);
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnect = async (platformId: string) => {
    if (!isAuthenticated || !tokens) {
      alert('Vui lòng đăng nhập để kết nối tài khoản');
      return;
    }

    setConnectingPlatform(platformId);

    try {
      // Get OAuth URL from backend
      const response = await fetch(`${API_BASE_URL}/api/platforms/oauth/${platformId}/url`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Không thể lấy OAuth URL');
      }

      const data = await response.json();

      // Redirect to Facebook/Platform authorization
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('Connection error:', error);
      alert(`Lỗi kết nối: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setConnectingPlatform(null);
    }
  };

  const handleDisconnect = async (accountId: number) => {
    if (!confirm('Bạn có chắc muốn ngắt kết nối tài khoản này?')) return;
    if (!tokens) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/platforms/accounts/${accountId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (!response.ok) {
        throw new Error('Không thể ngắt kết nối');
      }

      // Remove from local state
      setAccounts(accounts.filter(a => a.id !== accountId));
      alert('Đã ngắt kết nối tài khoản');
    } catch (error) {
      console.error('Disconnect error:', error);
      alert(`Lỗi: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleRefreshToken = async (accountId: number) => {
    if (!tokens) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/platforms/accounts/${accountId}/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`
        }
      });

      if (!response.ok) {
        throw new Error('Không thể làm mới token');
      }

      alert('Đã làm mới token thành công');
      // Refresh accounts list
      fetchData();
    } catch (error) {
      console.error('Refresh error:', error);
      alert(`Lỗi: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const getAccountsByPlatform = (platformId: string) => {
    return accounts.filter(a => a.platform === platformId);
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-gray-600">Đang tải...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-gray-900 mb-2">Quản lý tài khoản</h2>
        <p className="text-gray-600">Kết nối và quản lý các tài khoản mạng xã hội</p>
      </div>

      {/* Platform Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {platforms.map((platform) => {
          const Icon = platformIcons[platform.id] || Settings;
          const connectedAccounts = getAccountsByPlatform(platform.id);
          const isConnected = connectedAccounts.length > 0;

          return (
            <div
              key={platform.id}
              className={`bg-white rounded-xl border-2 transition-all ${
                isConnected ? 'border-green-200' : 'border-gray-200'
              }`}
            >
              {/* Platform Header */}
              <div className={`p-4 rounded-t-xl ${platformColors[platform.id]} text-white`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon className="w-8 h-8" />
                    <div>
                      <h3 className="font-semibold">{platform.name}</h3>
                      <p className="text-sm opacity-80">
                        {connectedAccounts.length} tài khoản đã kết nối
                      </p>
                    </div>
                  </div>
                  {isConnected && (
                    <div className="bg-white/20 rounded-full p-1">
                      <Check className="w-5 h-5" />
                    </div>
                  )}
                </div>
              </div>

              {/* Connected Accounts */}
              <div className="p-4">
                {connectedAccounts.length > 0 ? (
                  <div className="space-y-3 mb-4">
                    {connectedAccounts.map((account) => (
                      <div
                        key={account.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          {account.profile_picture_url ? (
                            <ImageWithFallback
                              src={account.profile_picture_url}
                              alt={account.name}
                              className="w-10 h-10 rounded-full object-cover"
                            />
                          ) : (
                            <div className={`w-10 h-10 rounded-full ${platformColors[platform.id]} flex items-center justify-center text-white`}>
                              {account.name.charAt(0).toUpperCase()}
                            </div>
                          )}
                          <div>
                            <p className="font-medium text-gray-900">{account.name}</p>
                            {account.username && (
                              <p className="text-sm text-gray-500">@{account.username}</p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {account.is_token_expired && (
                            <span className="text-amber-500" title="Token hết hạn">
                              <AlertCircle className="w-5 h-5" />
                            </span>
                          )}
                          <button
                            onClick={() => handleRefreshToken(account.id)}
                            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="Làm mới token"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDisconnect(account.id)}
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                            title="Ngắt kết nối"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm mb-4">
                    Chưa có tài khoản nào được kết nối
                  </p>
                )}

                {/* Supported Features */}
                <div className="mb-4">
                  <p className="text-xs text-gray-500 mb-2">Tính năng hỗ trợ:</p>
                  <div className="flex flex-wrap gap-1">
                    {platform.supported_features.map((feature) => (
                      <span
                        key={feature}
                        className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Connect Button */}
                <button
                  onClick={() => handleConnect(platform.id)}
                  disabled={connectingPlatform === platform.id}
                  className={`w-full py-2 rounded-lg flex items-center justify-center gap-2 transition-colors ${
                    isConnected
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      : `${platformColors[platform.id]} text-white hover:opacity-90`
                  }`}
                >
                  {connectingPlatform === platform.id ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Đang kết nối...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      {isConnected ? 'Thêm tài khoản' : 'Kết nối'}
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Setup Guide */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
        <h3 className="text-gray-900 mb-3 flex items-center gap-2">
          <Settings className="w-5 h-5 text-blue-600" />
          Hướng dẫn cài đặt
        </h3>
        <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-600">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Facebook & Instagram</h4>
            <ol className="list-decimal list-inside space-y-1">
              <li>Tạo Facebook App tại developers.facebook.com</li>
              <li>Thêm Facebook Login và Pages API</li>
              <li>Cấu hình OAuth redirect URI</li>
              <li>Kết nối Instagram Business với Facebook Page</li>
            </ol>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Zalo & TikTok (Coming Soon)</h4>
            <ol className="list-decimal list-inside space-y-1">
              <li>Đăng ký Zalo OA hoặc TikTok for Business</li>
              <li>Tạo ứng dụng và lấy credentials</li>
              <li>Cấu hình trong file .env</li>
            </ol>
          </div>
        </div>
        <a
          href="/api/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-4 text-blue-600 hover:text-blue-700"
        >
          Xem hướng dẫn chi tiết
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </div>
  );
}
