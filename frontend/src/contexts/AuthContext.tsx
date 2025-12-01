import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: number;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  avatar?: string;
  is_facebook_connected: boolean;
  facebook_user_id?: string;
  created_at: string;
}

interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthContextType {
  user: User | null;
  tokens: Tokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string, confirmPassword: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Dynamic API URL - uses NEXT_PUBLIC_API_URL from env, fallback to same origin
const getApiUrl = () => {
  // Ưu tiên dùng env variable
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // Fallback: dynamic detection
  if (typeof window !== 'undefined') {
    // Development: localhost dùng port 8000
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return `http://${window.location.hostname}:8000`;
    }
    // Production: cùng origin (Nginx sẽ proxy /api → backend)
    return `${window.location.protocol}//${window.location.host}`;
  }
  return 'http://localhost:8000';
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<Tokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load tokens from localStorage on mount
  useEffect(() => {
    const savedTokens = localStorage.getItem('tokens');
    const savedUser = localStorage.getItem('user');

    if (savedTokens && savedUser) {
      setTokens(JSON.parse(savedTokens));
      setUser(JSON.parse(savedUser));
    }
    setIsLoading(false);
  }, []);

  // Save to localStorage when tokens/user change
  useEffect(() => {
    if (tokens) {
      localStorage.setItem('tokens', JSON.stringify(tokens));
    } else {
      localStorage.removeItem('tokens');
    }
  }, [tokens]);

  useEffect(() => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user));
    } else {
      localStorage.removeItem('user');
    }
  }, [user]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    console.log(`[AUTH] Đang đăng nhập với email: ${email}`);

    try {
      const response = await fetch(`${getApiUrl()}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail || 'Đăng nhập thất bại';
        console.error(`[AUTH_ERROR] Đăng nhập thất bại cho email: ${email}`);
        console.error(`[AUTH_ERROR] Lý do: ${errorMessage}`);
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log(`[AUTH_SUCCESS] Đăng nhập thành công: ${email}`);
      setUser(data.user);
      setTokens(data.tokens);
      // Navigation handled by LoginPage component
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, username: string, password: string, confirmPassword: string) => {
    setIsLoading(true);
    console.log(`[AUTH] Đang đăng ký tài khoản: ${email} (username: ${username})`);

    try {
      const response = await fetch(`${getApiUrl()}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          username,
          password,
          confirm_password: confirmPassword,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail || 'Đăng ký thất bại';
        console.error(`[AUTH_ERROR] Đăng ký thất bại cho email: ${email}`);
        console.error(`[AUTH_ERROR] Lý do: ${errorMessage}`);
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log(`[AUTH_SUCCESS] Đăng ký thành công: ${email}`);
      setUser(data.user);
      setTokens(data.tokens);
      // Navigation handled by RegisterPage component
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (tokens?.access_token) {
        await fetch(`${getApiUrl()}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${tokens.access_token}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setTokens(null);
      localStorage.removeItem('tokens');
      localStorage.removeItem('user');
      // Redirect to login page
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  };

  const refreshToken = async () => {
    if (!tokens?.refresh_token) return;

    try {
      const response = await fetch(`${getApiUrl()}/api/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const newTokens = await response.json();
      setTokens(newTokens);
    } catch (error) {
      console.error('Token refresh error:', error);
      await logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        tokens,
        isAuthenticated: !!user && !!tokens,
        isLoading,
        login,
        register,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
