'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Save,
  RefreshCw,
  Upload,
  Phone,
  Globe,
  Type,
  Palette,
  X,
  CheckCircle,
  AlertCircle,
  Plus,
  Sparkles,
  ImageIcon,
  Trash2,
} from 'lucide-react';
import { agentService, AgentSettings as AgentSettingsType } from '@/services/agentService';

// Helper to get full media URL
const getMediaUrl = (path: string | null | undefined): string => {
  if (!path) return '';
  if (path.startsWith('http')) return path; // Already full URL

  // Get API base URL
  const apiUrl = typeof window !== 'undefined'
    ? (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? `http://${window.location.hostname}:8000`
      : `${window.location.protocol}//${window.location.host}`
    : 'http://localhost:8000';

  return `${apiUrl}${path}`;
};

const LOGO_POSITIONS = [
  { value: 'top_left', label: 'Trên trái' },
  { value: 'top_right', label: 'Trên phải' },
  { value: 'bottom_left', label: 'Dưới trái' },
  { value: 'bottom_right', label: 'Dưới phải' },
  { value: 'center', label: 'Giữa' },
];


export function AgentSettings() {
  const [settings, setSettings] = useState<AgentSettingsType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [newColor, setNewColor] = useState('#3B82F6');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form state
  const [formData, setFormData] = useState<Partial<AgentSettingsType>>({});

  // Load settings
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await agentService.getSettings();
        setSettings(data);
        setFormData(data);
      } catch (err) {
        setError('Không thể tải cài đặt');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, []);

  // Auto hide messages
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Handle save
  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await agentService.updateSettings(formData);
      setSuccess('Đã lưu cài đặt thành công');
      setSettings(formData as AgentSettingsType);
    } catch (err) {
      setError('Không thể lưu cài đặt');
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle logo upload
  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsSaving(true);
      const logo = await agentService.uploadLogo(file);
      setFormData(prev => ({
        ...prev,
        logo_id: logo.id,
        logo_url: logo.url,
      }));
      setSuccess('Đã upload logo thành công');
    } catch (err) {
      setError('Không thể upload logo');
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  // Handle remove logo
  const handleRemoveLogo = () => {
    setFormData(prev => ({
      ...prev,
      logo_id: null,
      logo_url: null,
    }));
  };

  // Handle add color
  const handleAddColor = () => {
    const currentColors = formData.brand_colors || [];
    if (currentColors.length >= 5) {
      setError('Chỉ được thêm tối đa 5 màu');
      return;
    }
    if (!currentColors.includes(newColor)) {
      setFormData(prev => ({
        ...prev,
        brand_colors: [...currentColors, newColor],
      }));
    }
  };

  // Handle remove color
  const handleRemoveColor = (color: string) => {
    setFormData(prev => ({
      ...prev,
      brand_colors: (prev.brand_colors || []).filter(c => c !== color),
    }));
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-violet-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-gray-600">Đang tải cài đặt...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gradient-to-br from-violet-50/50 via-white to-purple-50/50">
      <div className="max-w-5xl mx-auto p-6 lg:p-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-200">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Cài đặt Fugu</h1>
              <p className="text-gray-500 mt-0.5">Tùy chỉnh AI Assistant theo phong cách của bạn</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-2xl flex items-center gap-3 animate-in slide-in-from-top-2">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-red-600" />
            </div>
            <p className="text-red-700 flex-1">{error}</p>
            <button onClick={() => setError(null)} className="p-1 hover:bg-red-100 rounded-lg transition-colors">
              <X className="w-4 h-4 text-red-400" />
            </button>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-100 rounded-2xl flex items-center gap-3 animate-in slide-in-from-top-2">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-green-700 flex-1">{success}</p>
            <button onClick={() => setSuccess(null)} className="p-1 hover:bg-green-100 rounded-lg transition-colors">
              <X className="w-4 h-4 text-green-400" />
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Logo & Branding */}
          <div className="lg:col-span-2 space-y-6">
            {/* Logo Card */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-violet-50 to-purple-50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-violet-100 flex items-center justify-center">
                    <ImageIcon className="w-4 h-4 text-violet-600" />
                  </div>
                  <h2 className="font-semibold text-gray-900">Logo & Thương hiệu</h2>
                </div>
              </div>

              <div className="p-6">
                <div className="flex flex-col sm:flex-row gap-6">
                  {/* Logo Preview */}
                  <div className="flex-shrink-0">
                    <p className="text-sm font-medium text-gray-700 mb-3">Logo hiện tại</p>
                    <div
                      className="w-32 h-32 rounded-2xl border-2 border-dashed border-gray-200 flex items-center justify-center bg-gray-50 overflow-hidden cursor-pointer hover:border-violet-300 hover:bg-violet-50 transition-all group"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {formData.logo_url ? (
                        <div className="relative w-full h-full">
                          <img
                            src={getMediaUrl(formData.logo_url)}
                            alt="Logo"
                            className="w-full h-full object-contain p-2"
                          />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRemoveLogo();
                            }}
                            className="absolute top-1 right-1 p-1.5 bg-red-500 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <Trash2 className="w-3 h-3 text-white" />
                          </button>
                        </div>
                      ) : (
                        <div className="text-center">
                          <Upload className="w-8 h-8 text-gray-300 mx-auto mb-2 group-hover:text-violet-400 transition-colors" />
                          <span className="text-xs text-gray-400 group-hover:text-violet-500">Click để tải lên</span>
                        </div>
                      )}
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleLogoUpload}
                      className="hidden"
                    />
                    <p className="text-xs text-gray-400 mt-2 text-center">PNG, JPG (max 2MB)</p>
                  </div>

                  {/* Logo Position */}
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-700 mb-3">Vị trí logo trên ảnh</p>
                    {/* Position Grid Preview */}
                    <div className="relative w-full aspect-video bg-gradient-to-br from-gray-100 to-gray-50 rounded-xl border border-gray-200 mb-4">
                      {/* Position dots */}
                      {LOGO_POSITIONS.map(pos => {
                        const posStyles: Record<string, string> = {
                          'top_left': 'top-2 left-2',
                          'top_right': 'top-2 right-2',
                          'bottom_left': 'bottom-2 left-2',
                          'bottom_right': 'bottom-2 right-2',
                          'center': 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2',
                        };
                        return (
                          <button
                            key={pos.value}
                            onClick={() => setFormData(prev => ({ ...prev, logo_position: pos.value as any }))}
                            className={`absolute ${posStyles[pos.value]} w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                              formData.logo_position === pos.value
                                ? 'bg-violet-500 text-white shadow-lg scale-110'
                                : 'bg-white text-gray-400 border border-gray-200 hover:border-violet-300 hover:text-violet-500'
                            }`}
                            title={pos.label}
                          >
                            {formData.logo_url && formData.logo_position === pos.value ? (
                              <img src={getMediaUrl(formData.logo_url)} alt="" className="w-5 h-5 object-contain" />
                            ) : (
                              <div className="w-3 h-3 rounded-sm bg-current opacity-50" />
                            )}
                          </button>
                        );
                      })}
                      {/* Center text */}
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <span className="text-xs text-gray-300">Preview vị trí logo</span>
                      </div>
                    </div>

                    {/* Logo Size */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-600">Kích thước</span>
                        <span className="text-sm font-medium text-violet-600">{formData.logo_size || 15}%</span>
                      </div>
                      <input
                        type="range"
                        min="5"
                        max="30"
                        value={formData.logo_size || 15}
                        onChange={(e) => setFormData(prev => ({ ...prev, logo_size: parseInt(e.target.value) }))}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-violet-600"
                      />
                    </div>

                    {/* Auto Add Logo */}
                    <label className="flex items-center justify-between mt-4 p-3 bg-gray-50 rounded-xl cursor-pointer hover:bg-gray-100 transition-colors">
                      <div>
                        <span className="text-sm font-medium text-gray-700">Tự động thêm logo</span>
                        <p className="text-xs text-gray-500">Thêm logo vào tất cả ảnh được tạo</p>
                      </div>
                      <div className="relative">
                        <input
                          type="checkbox"
                          checked={formData.auto_add_logo || false}
                          onChange={(e) => setFormData(prev => ({ ...prev, auto_add_logo: e.target.checked }))}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-violet-100 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-violet-600"></div>
                      </div>
                    </label>
                  </div>
                </div>

                {/* Brand Colors */}
                <div className="mt-6 pt-6 border-t border-gray-100">
                  <div className="flex items-center gap-2 mb-4">
                    <Palette className="w-4 h-4 text-violet-500" />
                    <span className="text-sm font-medium text-gray-700">Màu thương hiệu</span>
                    <span className="text-xs text-gray-400">(tối đa 5)</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    {(formData.brand_colors || []).map((color, index) => (
                      <div key={index} className="relative group">
                        <div
                          className="w-12 h-12 rounded-xl shadow-sm border-2 border-white ring-1 ring-gray-200"
                          style={{ backgroundColor: color }}
                        />
                        <button
                          onClick={() => handleRemoveColor(color)}
                          className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                        >
                          <X className="w-3 h-3 text-white" />
                        </button>
                      </div>
                    ))}
                    {(formData.brand_colors || []).length < 5 && (
                      <div className="flex items-center gap-2">
                        <input
                          type="color"
                          value={newColor}
                          onChange={(e) => setNewColor(e.target.value)}
                          className="w-12 h-12 rounded-xl cursor-pointer border-2 border-white ring-1 ring-gray-200"
                        />
                        <button
                          onClick={handleAddColor}
                          className="w-12 h-12 border-2 border-dashed border-gray-300 rounded-xl flex items-center justify-center hover:border-violet-400 hover:bg-violet-50 transition-colors"
                        >
                          <Plus className="w-5 h-5 text-gray-400" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Slogan */}
                <div className="mt-6 pt-6 border-t border-gray-100">
                  <div className="flex items-center gap-2 mb-3">
                    <Type className="w-4 h-4 text-violet-500" />
                    <span className="text-sm font-medium text-gray-700">Slogan / Tagline</span>
                  </div>
                  <input
                    type="text"
                    value={formData.slogan || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, slogan: e.target.value }))}
                    placeholder="VD: Chất lượng là danh dự"
                    maxLength={200}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:border-violet-500 focus:bg-white transition-all"
                  />
                </div>
              </div>
            </div>

            {/* Contact Card */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-cyan-50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                    <Phone className="w-4 h-4 text-blue-600" />
                  </div>
                  <h2 className="font-semibold text-gray-900">Thông tin liên hệ</h2>
                </div>
              </div>

              <div className="p-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <Phone className="w-4 h-4 text-gray-400" />
                      Hotline
                    </label>
                    <input
                      type="tel"
                      value={formData.hotline || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, hotline: e.target.value }))}
                      placeholder="0901 234 567"
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition-all"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <Globe className="w-4 h-4 text-gray-400" />
                      Website
                    </label>
                    <input
                      type="url"
                      value={formData.website || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, website: e.target.value }))}
                      placeholder="https://example.com"
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition-all"
                    />
                  </div>
                </div>

                <label className="flex items-center justify-between mt-4 p-3 bg-gray-50 rounded-xl cursor-pointer hover:bg-gray-100 transition-colors">
                  <div>
                    <span className="text-sm font-medium text-gray-700">Tự động thêm hotline</span>
                    <p className="text-xs text-gray-500">Thêm số điện thoại vào cuối mỗi bài đăng</p>
                  </div>
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={formData.auto_add_hotline || false}
                      onChange={(e) => setFormData(prev => ({ ...prev, auto_add_hotline: e.target.checked }))}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-100 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Right Column - Content Settings */}
          <div className="space-y-6">
            {/* Word Count */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-emerald-50 to-teal-50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
                    <Type className="w-4 h-4 text-emerald-600" />
                  </div>
                  <h2 className="font-semibold text-gray-900">Độ dài bài viết</h2>
                </div>
              </div>

              <div className="p-6">
                <div className="text-center mb-4">
                  <span className="text-4xl font-bold text-gray-900">{formData.default_word_count || 100}</span>
                  <span className="text-gray-500 ml-2">từ</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="500"
                  step="10"
                  value={formData.default_word_count || 100}
                  onChange={(e) => setFormData(prev => ({ ...prev, default_word_count: parseInt(e.target.value) }))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-2">
                  <span>Ngắn</span>
                  <span>Vừa</span>
                  <span>Dài</span>
                </div>
              </div>
            </div>

            {/* Save Button */}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 disabled:from-violet-400 disabled:to-purple-400 text-white rounded-2xl font-medium transition-all shadow-lg shadow-violet-200 hover:shadow-xl hover:shadow-violet-300"
            >
              {isSaving ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Đang lưu...
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  Lưu cài đặt
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
