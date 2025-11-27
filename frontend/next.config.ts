import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Cho phép truy cập từ máy khác trong mạng LAN
  // Tương tự host: true trong Vite

  // Cấu hình images để load từ external sources
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'http',
        hostname: '192.168.31.31',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
    ],
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // TypeScript
  typescript: {
    // Bỏ qua lỗi TypeScript khi build (cho development)
    ignoreBuildErrors: true,
  },

  // ESLint
  eslint: {
    ignoreDuringBuilds: true,
  },
}

export default nextConfig
