import { useState } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Link as LinkIcon } from 'lucide-react';

interface Token {
  pageId: string;
  pageName: string;
  status: 'active' | 'expiring' | 'expired';
  expiryDate: Date;
  lastRefresh: Date;
  autoRefresh: boolean;
}

const mockTokens: Token[] = [
  {
    pageId: '123456789',
    pageName: 'Page Kinh Doanh Online',
    status: 'active',
    expiryDate: new Date(2025, 11, 20),
    lastRefresh: new Date(2025, 10, 1),
    autoRefresh: true,
  },
  {
    pageId: '987654321',
    pageName: 'Shop Thời Trang ABC',
    status: 'expiring',
    expiryDate: new Date(2025, 10, 25),
    lastRefresh: new Date(2025, 9, 15),
    autoRefresh: true,
  },
  {
    pageId: '456789123',
    pageName: 'Cộng đồng Marketing',
    status: 'active',
    expiryDate: new Date(2025, 11, 15),
    lastRefresh: new Date(2025, 10, 10),
    autoRefresh: false,
  },
  {
    pageId: '789123456',
    pageName: 'Nhà Hàng Ngon',
    status: 'expired',
    expiryDate: new Date(2025, 10, 10),
    lastRefresh: new Date(2025, 8, 1),
    autoRefresh: false,
  },
];

export function TokenManagement() {
  const [tokens, setTokens] = useState<Token[]>(mockTokens);
  const [showConnect, setShowConnect] = useState(false);

  const getDaysUntilExpiry = (expiryDate: Date) => {
    const today = new Date(2025, 10, 20); // Mock today
    const diffTime = expiryDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getStatusIcon = (status: Token['status']) => {
    switch (status) {
      case 'active':
        return <CheckCircle2 className="w-6 h-6 text-green-500" />;
      case 'expiring':
        return <AlertTriangle className="w-6 h-6 text-yellow-500" />;
      case 'expired':
        return <XCircle className="w-6 h-6 text-red-500" />;
    }
  };

  const getStatusText = (status: Token['status']) => {
    switch (status) {
      case 'active':
        return 'Đang hoạt động';
      case 'expiring':
        return 'Sắp hết hạn';
      case 'expired':
        return 'Đã hết hạn';
    }
  };

  const toggleAutoRefresh = (pageId: string) => {
    setTokens(
      tokens.map((token) =>
        token.pageId === pageId
          ? { ...token, autoRefresh: !token.autoRefresh }
          : token
      )
    );
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h2 className="text-gray-900 mb-2">Quản lý Token</h2>
          <p className="text-gray-600">Theo dõi và quản lý kết nối Facebook</p>
        </div>
        <button
          onClick={() => setShowConnect(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <LinkIcon className="w-4 h-4" />
          Kết nối Page mới
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-gray-600 text-sm">Đang hoạt động</p>
              <p className="text-gray-900">
                {tokens.filter((t) => t.status === 'active').length} pages
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-yellow-100 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-gray-600 text-sm">Sắp hết hạn</p>
              <p className="text-gray-900">
                {tokens.filter((t) => t.status === 'expiring').length} pages
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
              <XCircle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-gray-600 text-sm">Đã hết hạn</p>
              <p className="text-gray-900">
                {tokens.filter((t) => t.status === 'expired').length} pages
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Token list */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-sm text-gray-600">Trạng thái</th>
                <th className="px-6 py-4 text-left text-sm text-gray-600">Page</th>
                <th className="px-6 py-4 text-left text-sm text-gray-600">Page ID</th>
                <th className="px-6 py-4 text-left text-sm text-gray-600">Hết hạn</th>
                <th className="px-6 py-4 text-left text-sm text-gray-600">Làm mới lần cuối</th>
                <th className="px-6 py-4 text-left text-sm text-gray-600">Auto Refresh</th>
                <th className="px-6 py-4 text-left text-sm text-gray-600">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {tokens.map((token) => {
                const daysLeft = getDaysUntilExpiry(token.expiryDate);
                return (
                  <tr key={token.pageId} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(token.status)}
                        <div>
                          <p className="text-sm text-gray-900">{getStatusText(token.status)}</p>
                          {token.status !== 'expired' && (
                            <p className="text-xs text-gray-500">
                              {daysLeft > 0 ? `${daysLeft} ngày` : 'Hết hạn'}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-900">{token.pageName}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-700 font-mono">{token.pageId}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-700">
                        {token.expiryDate.toLocaleDateString('vi-VN')}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-700">
                        {token.lastRefresh.toLocaleDateString('vi-VN')}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={token.autoRefresh}
                          onChange={() => toggleAutoRefresh(token.pageId)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </td>
                    <td className="px-6 py-4">
                      {token.status === 'expired' ? (
                        <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2 text-sm">
                          <LinkIcon className="w-4 h-4" />
                          Kết nối lại
                        </button>
                      ) : (
                        <button className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 flex items-center gap-2 text-sm">
                          <RefreshCw className="w-4 h-4" />
                          Làm mới
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info box */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-blue-900 mb-2">💡 Lưu ý về Token</h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li>• Token Facebook có thời hạn 60-90 ngày tùy loại</li>
          <li>• Bật "Auto Refresh" để tự động gia hạn token trước khi hết hạn</li>
          <li>• Token được mã hóa và lưu trữ an toàn trong database</li>
          <li>• Nếu token hết hạn, bạn cần kết nối lại để lấy token mới</li>
        </ul>
      </div>

      {/* Connect Modal */}
      {showConnect && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-gray-900">Kết nối Facebook Page</h3>
              <button
                onClick={() => setShowConnect(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <p className="text-gray-600">
                Bạn sẽ được chuyển đến Facebook để cấp quyền truy cập cho ứng dụng.
              </p>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-800">
                  <span>⚠️ Quyền cần thiết:</span>
                  <ul className="mt-2 ml-4 space-y-1">
                    <li>• pages_show_list - Xem danh sách Page</li>
                    <li>• pages_read_engagement - Đọc thống kê</li>
                    <li>• pages_manage_posts - Đăng bài</li>
                    <li>• pages_manage_engagement - Quản lý tương tác</li>
                  </ul>
                </p>
              </div>

              <button className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                Kết nối với Facebook
              </button>

              <button
                onClick={() => setShowConnect(false)}
                className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Hủy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
