'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Facebook,
  Settings,
  Save,
  RefreshCw,
  Image,
  Camera,
  Globe,
  Phone,
  Mail,
  FileText,
  Users,
  ExternalLink,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  X,
} from 'lucide-react';
import { ImageWithFallback } from './figma/ImageWithFallback';
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

interface PageDetails {
  id: string;
  name: string;
  username?: string;
  about: string;
  description: string;
  category?: string;
  category_list: { id: string; name: string }[];
  phone: string;
  website: string;
  emails: string[];
  single_line_address: string;
  location: Record<string, any>;
  hours: Record<string, any>;
  cover: { source?: string; offset_y?: number };
  picture: { url?: string };
  fan_count: number;
  followers_count: number;
  link: string;
}

interface MediaItem {
  id: number;
  file_url: string;
  file_type: string;
  file_size: number;
  width?: number;
  height?: number;
  folder_id?: number;
  folder_name?: string;
  created_at: string;
}

// Helper to get full media URL (file_url might be relative like /media/uploads/...)
const getFullMediaUrl = (fileUrl: string, apiBaseUrl: string): string => {
  if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) {
    return fileUrl;
  }
  // Remove trailing slash from apiBaseUrl if present
  const baseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
  return `${baseUrl}${fileUrl}`;
};

export function PageSettings() {
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [pageDetails, setPageDetails] = useState<PageDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showAccountDropdown, setShowAccountDropdown] = useState(false);

  // Edit form state
  const [editForm, setEditForm] = useState({
    about: '',
    description: '',
    phone: '',
    website: '',
    emails: '',
  });

  // Media picker state
  const [showMediaPicker, setShowMediaPicker] = useState(false);
  const [mediaPickerType, setMediaPickerType] = useState<'picture' | 'cover'>('picture');
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);

  // Bulk update state
  const [bulkForm, setBulkForm] = useState({
    website: '',
    about: '',
    description: '',
    phone: '',
    emails: '',
  });
  const [selectedAccountIds, setSelectedAccountIds] = useState<number[]>([]);
  const [isBulkUpdating, setIsBulkUpdating] = useState(false);
  const [bulkResults, setBulkResults] = useState<{
    total: number;
    succeeded: number;
    failed: number;
    results: { account_id: number; account_name: string; success: boolean; error?: string }[];
  } | null>(null);
  const [showBulkMediaPicker, setShowBulkMediaPicker] = useState(false);
  const [bulkMediaType, setBulkMediaType] = useState<'picture' | 'cover'>('picture');

  const { tokens } = useAuth();
  const API_BASE_URL = getApiUrl();

  // Fetch Facebook accounts
  useEffect(() => {
    const fetchAccounts = async () => {
      if (!tokens) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/platforms/accounts?platform=facebook`, {
          headers: {
            Authorization: `Bearer ${tokens.access_token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setAccounts(data);
          if (data.length > 0) {
            setSelectedAccountId(data[0].id);
          }
        }
      } catch (error) {
        console.error('Error fetching accounts:', error);
        setError('Không thể tải danh sách tài khoản');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAccounts();
  }, [tokens, API_BASE_URL]);

  // Fetch page details when account is selected
  const fetchPageDetails = useCallback(async () => {
    if (!selectedAccountId || !tokens) return;

    setIsLoadingDetails(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/platforms/accounts/${selectedAccountId}/details`,
        {
          headers: {
            Authorization: `Bearer ${tokens.access_token}`,
          },
        }
      );

      const result = await response.json();

      if (result.success) {
        setPageDetails(result.data);
        setEditForm({
          about: result.data.about || '',
          description: result.data.description || '',
          phone: result.data.phone || '',
          website: result.data.website || '',
          emails: (result.data.emails || []).join(', '),
        });
      } else {
        setError(result.error || 'Không thể tải thông tin trang');
      }
    } catch (error) {
      console.error('Error fetching page details:', error);
      setError('Không thể tải thông tin trang');
    } finally {
      setIsLoadingDetails(false);
    }
  }, [selectedAccountId, tokens, API_BASE_URL]);

  useEffect(() => {
    fetchPageDetails();
  }, [fetchPageDetails]);

  // Fetch media library
  const fetchMediaLibrary = async () => {
    if (!tokens) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/media/`, {
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      if (response.ok) {
        const data: MediaItem[] = await response.json();
        // Filter images only on frontend
        const images = data.filter((item) => item.file_type === 'image');
        setMediaItems(images);
      }
    } catch (error) {
      console.error('Error fetching media:', error);
    }
  };

  // Handle save page info
  const handleSaveInfo = async () => {
    if (!selectedAccountId || !tokens) return;

    setIsSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const payload: Record<string, any> = {};

      if (editForm.about !== pageDetails?.about) {
        payload.about = editForm.about;
      }
      if (editForm.description !== pageDetails?.description) {
        payload.description = editForm.description;
      }
      if (editForm.phone !== pageDetails?.phone) {
        payload.phone = editForm.phone;
      }
      if (editForm.website !== pageDetails?.website) {
        payload.website = editForm.website;
      }
      const emailsArray = editForm.emails
        .split(',')
        .map((e) => e.trim())
        .filter((e) => e);
      if (JSON.stringify(emailsArray) !== JSON.stringify(pageDetails?.emails || [])) {
        payload.emails = emailsArray;
      }

      if (Object.keys(payload).length === 0) {
        setSuccess('Không có thay đổi để lưu');
        setIsSaving(false);
        return;
      }

      const response = await fetch(
        `${API_BASE_URL}/api/platforms/accounts/${selectedAccountId}/update`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${tokens.access_token}`,
          },
          body: JSON.stringify(payload),
        }
      );

      const result = await response.json();

      if (result.success) {
        setSuccess('Đã cập nhật thông tin trang thành công');
        fetchPageDetails();
      } else {
        setError(result.error || 'Không thể cập nhật thông tin');
      }
    } catch (error) {
      console.error('Error updating page info:', error);
      setError('Lỗi khi cập nhật thông tin');
    } finally {
      setIsSaving(false);
    }
  };

  // Handle photo update
  const handlePhotoUpdate = async (mediaId: number) => {
    if (!selectedAccountId || !tokens) return;

    setIsUploadingPhoto(true);
    setError(null);
    setSuccess(null);

    const endpoint =
      mediaPickerType === 'picture'
        ? `${API_BASE_URL}/api/platforms/accounts/${selectedAccountId}/picture`
        : `${API_BASE_URL}/api/platforms/accounts/${selectedAccountId}/cover`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tokens.access_token}`,
        },
        body: JSON.stringify({ media_id: mediaId }),
      });

      const result = await response.json();

      if (result.success) {
        setSuccess(
          mediaPickerType === 'picture'
            ? 'Đã cập nhật ảnh đại diện thành công'
            : 'Đã cập nhật ảnh bìa thành công'
        );
        setShowMediaPicker(false);
        fetchPageDetails();
      } else {
        setError(result.error || 'Không thể cập nhật ảnh');
      }
    } catch (error) {
      console.error('Error updating photo:', error);
      setError('Lỗi khi cập nhật ảnh');
    } finally {
      setIsUploadingPhoto(false);
    }
  };

  // Open media picker
  const openMediaPicker = (type: 'picture' | 'cover') => {
    setMediaPickerType(type);
    setShowMediaPicker(true);
    fetchMediaLibrary();
  };

  // Toggle select all accounts for bulk update
  const toggleSelectAll = () => {
    if (selectedAccountIds.length === accounts.length) {
      setSelectedAccountIds([]);
    } else {
      setSelectedAccountIds(accounts.map((a) => a.id));
    }
  };

  // Toggle single account selection
  const toggleAccountSelection = (accountId: number) => {
    setSelectedAccountIds((prev) =>
      prev.includes(accountId) ? prev.filter((id) => id !== accountId) : [...prev, accountId]
    );
  };

  // Handle bulk update info
  const handleBulkUpdateInfo = async () => {
    if (selectedAccountIds.length === 0 || !tokens) {
      setError('Vui lòng chọn ít nhất một trang');
      return;
    }

    // Check if any field has value
    const hasChanges = Object.values(bulkForm).some((v) => v.trim() !== '');
    if (!hasChanges) {
      setError('Vui lòng nhập ít nhất một thông tin cần cập nhật');
      return;
    }

    setIsBulkUpdating(true);
    setError(null);
    setSuccess(null);
    setBulkResults(null);

    try {
      const payload: Record<string, any> = {
        account_ids: selectedAccountIds,
      };

      if (bulkForm.about.trim()) payload.about = bulkForm.about;
      if (bulkForm.description.trim()) payload.description = bulkForm.description;
      if (bulkForm.phone.trim()) payload.phone = bulkForm.phone;
      if (bulkForm.website.trim()) payload.website = bulkForm.website;
      if (bulkForm.emails.trim()) {
        payload.emails = bulkForm.emails
          .split(',')
          .map((e) => e.trim())
          .filter((e) => e);
      }

      const response = await fetch(`${API_BASE_URL}/api/platforms/accounts/bulk-update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tokens.access_token}`,
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      setBulkResults(result);

      if (result.success) {
        setSuccess(`Đã cập nhật thành công ${result.succeeded}/${result.total} trang`);
      } else if (result.succeeded > 0) {
        setSuccess(`Cập nhật ${result.succeeded}/${result.total} trang. ${result.failed} trang thất bại.`);
      } else {
        setError(`Không thể cập nhật. Vui lòng kiểm tra lại.`);
      }
    } catch (error) {
      console.error('Bulk update error:', error);
      setError('Lỗi khi cập nhật hàng loạt');
    } finally {
      setIsBulkUpdating(false);
    }
  };

  // Handle bulk photo update
  const handleBulkPhotoUpdate = async (mediaId: number) => {
    if (selectedAccountIds.length === 0 || !tokens) return;

    setIsBulkUpdating(true);
    setError(null);
    setBulkResults(null);

    const endpoint =
      bulkMediaType === 'picture'
        ? `${API_BASE_URL}/api/platforms/accounts/bulk-picture`
        : `${API_BASE_URL}/api/platforms/accounts/bulk-cover`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tokens.access_token}`,
        },
        body: JSON.stringify({
          account_ids: selectedAccountIds,
          media_id: mediaId,
        }),
      });

      const result = await response.json();
      setBulkResults(result);

      if (result.success) {
        setSuccess(
          `Đã cập nhật ${bulkMediaType === 'picture' ? 'ảnh đại diện' : 'ảnh bìa'} cho ${result.succeeded}/${result.total} trang`
        );
      } else if (result.succeeded > 0) {
        setSuccess(`Cập nhật ${result.succeeded}/${result.total} trang. ${result.failed} trang thất bại.`);
      } else {
        setError('Không thể cập nhật ảnh');
      }
      setShowBulkMediaPicker(false);
    } catch (error) {
      console.error('Bulk photo update error:', error);
      setError('Lỗi khi cập nhật ảnh hàng loạt');
    } finally {
      setIsBulkUpdating(false);
    }
  };

  // Open bulk media picker
  const openBulkMediaPicker = (type: 'picture' | 'cover') => {
    if (selectedAccountIds.length === 0) {
      setError('Vui lòng chọn ít nhất một trang');
      return;
    }
    setBulkMediaType(type);
    setShowBulkMediaPicker(true);
    fetchMediaLibrary();
  };

  const selectedAccount = accounts.find((a) => a.id === selectedAccountId);

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

  if (accounts.length === 0) {
    return (
      <div className="p-8">
        <div className="text-center py-12">
          <Facebook className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Chưa có trang Facebook nào được kết nối
          </h3>
          <p className="text-gray-600 mb-4">
            Vui lòng kết nối tài khoản Facebook của bạn trong phần Tài khoản để sử dụng tính năng
            này.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Cài đặt trang</h2>
        <p className="text-gray-600">Quản lý thông tin và hình ảnh của trang Facebook</p>
      </div>

      <div className="flex gap-8">
        {/* Left Column - Single Page Settings */}
        <div className="flex-1 max-w-2xl">

      {/* Account Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Chọn trang</label>
        <div className="relative">
          <button
            onClick={() => setShowAccountDropdown(!showAccountDropdown)}
            className="w-full flex items-center justify-between p-3 bg-white border border-gray-300 rounded-lg hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {selectedAccount ? (
              <div className="flex items-center gap-3">
                {selectedAccount.profile_picture_url ? (
                  <ImageWithFallback
                    src={selectedAccount.profile_picture_url}
                    alt={selectedAccount.name}
                    className="w-8 h-8 rounded-full"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm">
                    {selectedAccount.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <span className="font-medium">{selectedAccount.name}</span>
              </div>
            ) : (
              <span className="text-gray-500">Chọn một trang...</span>
            )}
            <ChevronDown className="w-5 h-5 text-gray-400" />
          </button>

          {showAccountDropdown && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg">
              {accounts.map((account) => (
                <button
                  key={account.id}
                  onClick={() => {
                    setSelectedAccountId(account.id);
                    setShowAccountDropdown(false);
                  }}
                  className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
                >
                  {account.profile_picture_url ? (
                    <ImageWithFallback
                      src={account.profile_picture_url}
                      alt={account.name}
                      className="w-8 h-8 rounded-full"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm">
                      {account.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="text-left">
                    <p className="font-medium text-gray-900">{account.name}</p>
                    {account.category && (
                      <p className="text-sm text-gray-500">{account.category}</p>
                    )}
                  </div>
                  {account.id === selectedAccountId && (
                    <CheckCircle className="w-5 h-5 text-green-500 ml-auto" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4 text-red-400 hover:text-red-600" />
          </button>
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
          <p className="text-green-700">{success}</p>
          <button onClick={() => setSuccess(null)} className="ml-auto">
            <X className="w-4 h-4 text-green-400 hover:text-green-600" />
          </button>
        </div>
      )}

      {isLoadingDetails ? (
        <div className="text-center py-8">
          <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2" />
          <p className="text-gray-600">Đang tải thông tin trang...</p>
        </div>
      ) : pageDetails ? (
        <div className="space-y-6">
          {/* Cover & Profile Photo Section */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Cover Photo */}
            <div className="relative h-48 bg-gradient-to-r from-blue-500 to-blue-600">
              {pageDetails.cover?.source && (
                <img
                  src={pageDetails.cover.source}
                  alt="Cover"
                  className="w-full h-full object-cover"
                />
              )}
              <button
                onClick={() => openMediaPicker('cover')}
                className="absolute bottom-4 right-4 flex items-center gap-2 px-4 py-2 bg-black/50 hover:bg-black/70 text-white rounded-lg transition-colors"
              >
                <Camera className="w-4 h-4" />
                Đổi ảnh bìa
              </button>
            </div>

            {/* Profile Picture & Basic Info */}
            <div className="relative px-6 pb-6">
              <div className="flex items-end gap-4 -mt-12">
                <div className="relative">
                  <div className="w-24 h-24 rounded-xl border-4 border-white bg-white shadow-lg overflow-hidden">
                    {pageDetails.picture?.url ? (
                      <img
                        src={pageDetails.picture.url}
                        alt={pageDetails.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold">
                        {pageDetails.name?.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => openMediaPicker('picture')}
                    className="absolute bottom-0 right-0 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg transition-colors"
                    title="Đổi ảnh đại diện"
                  >
                    <Camera className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex-1 pt-14">
                  <h3 className="text-xl font-bold text-gray-900">{pageDetails.name}</h3>
                  <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                    {pageDetails.category && <span>{pageDetails.category}</span>}
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {pageDetails.followers_count?.toLocaleString() || 0} người theo dõi
                    </span>
                  </div>
                </div>

                {pageDetails.link && (
                  <a
                    href={pageDetails.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Xem trên Facebook
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* Page Information Form */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Settings className="w-5 h-5 text-blue-600" />
                Thông tin trang
              </h3>
              <button
                onClick={handleSaveInfo}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg transition-colors"
              >
                {isSaving ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Đang lưu...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Lưu thay đổi
                  </>
                )}
              </button>
            </div>

            <div className="space-y-4">
              {/* About */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <FileText className="w-4 h-4 inline mr-2" />
                  Giới thiệu ngắn (About)
                </label>
                <textarea
                  value={editForm.about}
                  onChange={(e) => setEditForm({ ...editForm, about: e.target.value })}
                  rows={2}
                  maxLength={255}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Mô tả ngắn gọn về trang..."
                />
                <p className="text-xs text-gray-500 mt-1">
                  {editForm.about.length}/255 ký tự
                </p>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <FileText className="w-4 h-4 inline mr-2" />
                  Mô tả chi tiết (Description)
                </label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Mô tả chi tiết về trang, sản phẩm, dịch vụ..."
                />
              </div>

              {/* Phone */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Phone className="w-4 h-4 inline mr-2" />
                  Số điện thoại
                </label>
                <input
                  type="tel"
                  value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="+84 xxx xxx xxx"
                />
              </div>

              {/* Website */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Globe className="w-4 h-4 inline mr-2" />
                  Website
                </label>
                <input
                  type="url"
                  value={editForm.website}
                  onChange={(e) => setEditForm({ ...editForm, website: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="https://example.com"
                />
              </div>

              {/* Emails */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Mail className="w-4 h-4 inline mr-2" />
                  Email (phân cách bằng dấu phẩy)
                </label>
                <input
                  type="text"
                  value={editForm.emails}
                  onChange={(e) => setEditForm({ ...editForm, emails: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="email1@example.com, email2@example.com"
                />
              </div>
            </div>
          </div>

          {/* Additional Info (Read-only) */}
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-4">Thông tin khác</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">ID trang:</span>
                <span className="ml-2 font-mono text-gray-900">{pageDetails.id}</span>
              </div>
              {pageDetails.username && (
                <div>
                  <span className="text-gray-500">Username:</span>
                  <span className="ml-2 text-gray-900">@{pageDetails.username}</span>
                </div>
              )}
              <div>
                <span className="text-gray-500">Lượt thích:</span>
                <span className="ml-2 text-gray-900">
                  {pageDetails.fan_count?.toLocaleString() || 0}
                </span>
              </div>
              {pageDetails.single_line_address && (
                <div>
                  <span className="text-gray-500">Địa chỉ:</span>
                  <span className="ml-2 text-gray-900">{pageDetails.single_line_address}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
        </div>

        {/* Right Column - Bulk Update */}
        <div className="w-96 flex-shrink-0">
          <div className="bg-white rounded-xl border border-gray-200 p-6 sticky top-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Cập nhật hàng loạt
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Áp dụng cùng một thông tin cho tất cả các trang đã chọn
            </p>

            {/* Account Selection */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  Chọn trang ({selectedAccountIds.length}/{accounts.length})
                </label>
                <button
                  onClick={toggleSelectAll}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  {selectedAccountIds.length === accounts.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
                </button>
              </div>
              <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg">
                {accounts.map((account) => (
                  <label
                    key={account.id}
                    className="flex items-center gap-3 p-2 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedAccountIds.includes(account.id)}
                      onChange={() => toggleAccountSelection(account.id)}
                      className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                    />
                    {account.profile_picture_url ? (
                      <ImageWithFallback
                        src={account.profile_picture_url}
                        alt={account.name}
                        className="w-6 h-6 rounded-full"
                      />
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs">
                        {account.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <span className="text-sm text-gray-700 truncate">{account.name}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Bulk Update Form */}
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Globe className="w-4 h-4 inline mr-1" />
                  Website
                </label>
                <input
                  type="url"
                  value={bulkForm.website}
                  onChange={(e) => setBulkForm({ ...bulkForm, website: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="https://example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <FileText className="w-4 h-4 inline mr-1" />
                  Giới thiệu ngắn
                </label>
                <input
                  type="text"
                  value={bulkForm.about}
                  onChange={(e) => setBulkForm({ ...bulkForm, about: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Mô tả ngắn (255 ký tự)"
                  maxLength={255}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Phone className="w-4 h-4 inline mr-1" />
                  Số điện thoại
                </label>
                <input
                  type="tel"
                  value={bulkForm.phone}
                  onChange={(e) => setBulkForm({ ...bulkForm, phone: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="+84 xxx xxx xxx"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Mail className="w-4 h-4 inline mr-1" />
                  Email
                </label>
                <input
                  type="text"
                  value={bulkForm.emails}
                  onChange={(e) => setBulkForm({ ...bulkForm, emails: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="email@example.com"
                />
              </div>

              <button
                onClick={handleBulkUpdateInfo}
                disabled={isBulkUpdating || selectedAccountIds.length === 0}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isBulkUpdating ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Cập nhật thông tin
              </button>
            </div>

            {/* Bulk Photo Update */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Cập nhật ảnh hàng loạt</h4>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => openBulkMediaPicker('picture')}
                  disabled={isBulkUpdating || selectedAccountIds.length === 0}
                  className="flex items-center justify-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Camera className="w-4 h-4" />
                  Ảnh đại diện
                </button>
                <button
                  onClick={() => openBulkMediaPicker('cover')}
                  disabled={isBulkUpdating || selectedAccountIds.length === 0}
                  className="flex items-center justify-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Image className="w-4 h-4" />
                  Ảnh bìa
                </button>
              </div>
            </div>

            {/* Bulk Results */}
            {bulkResults && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="text-sm font-medium text-gray-700 mb-2">
                  Kết quả: {bulkResults.succeeded}/{bulkResults.total} thành công
                </div>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {bulkResults.results.map((r) => (
                    <div
                      key={r.account_id}
                      className={`text-xs flex items-center gap-1 ${r.success ? 'text-green-600' : 'text-red-600'}`}
                    >
                      {r.success ? (
                        <CheckCircle className="w-3 h-3" />
                      ) : (
                        <AlertCircle className="w-3 h-3" />
                      )}
                      <span className="truncate">{r.account_name}</span>
                      {r.error && <span className="text-red-500">- {r.error}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Media Picker Modal */}
      {showMediaPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="relative bg-white rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold">
                {mediaPickerType === 'picture' ? 'Chọn ảnh đại diện' : 'Chọn ảnh bìa'}
              </h3>
              <button
                onClick={() => setShowMediaPicker(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {mediaItems.length > 0 ? (
                <div className="grid grid-cols-4 gap-3">
                  {mediaItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handlePhotoUpdate(item.id)}
                      disabled={isUploadingPhoto}
                      className="relative aspect-square rounded-lg overflow-hidden border-2 border-transparent hover:border-blue-500 transition-colors disabled:opacity-50"
                    >
                      <img
                        src={getFullMediaUrl(item.file_url, API_BASE_URL)}
                        alt={`Media ${item.id}`}
                        className="w-full h-full object-cover"
                      />
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Image className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-500">Không có hình ảnh trong thư viện</p>
                  <p className="text-sm text-gray-400 mt-1">
                    Vui lòng tải lên hình ảnh trong mục Thư viện
                  </p>
                </div>
              )}
            </div>

            {isUploadingPhoto && (
              <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
                <div className="text-center">
                  <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2" />
                  <p className="text-gray-600">Đang cập nhật ảnh...</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bulk Media Picker Modal */}
      {showBulkMediaPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="relative bg-white rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-semibold">
                  {bulkMediaType === 'picture' ? 'Chọn ảnh đại diện' : 'Chọn ảnh bìa'} cho {selectedAccountIds.length} trang
                </h3>
                <p className="text-sm text-gray-500">
                  Ảnh sẽ được áp dụng cho tất cả các trang đã chọn
                </p>
              </div>
              <button
                onClick={() => setShowBulkMediaPicker(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {mediaItems.length > 0 ? (
                <div className="grid grid-cols-4 gap-3">
                  {mediaItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleBulkPhotoUpdate(item.id)}
                      disabled={isBulkUpdating}
                      className="relative aspect-square rounded-lg overflow-hidden border-2 border-transparent hover:border-blue-500 transition-colors disabled:opacity-50"
                    >
                      <img
                        src={getFullMediaUrl(item.file_url, API_BASE_URL)}
                        alt={`Media ${item.id}`}
                        className="w-full h-full object-cover"
                      />
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Image className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                  <p className="text-gray-500">Không có hình ảnh trong thư viện</p>
                  <p className="text-sm text-gray-400 mt-1">
                    Vui lòng tải lên hình ảnh trong mục Thư viện
                  </p>
                </div>
              )}
            </div>

            {isBulkUpdating && (
              <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
                <div className="text-center">
                  <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2" />
                  <p className="text-gray-600">Đang cập nhật ảnh cho {selectedAccountIds.length} trang...</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
