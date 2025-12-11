/**
 * Agent API Service
 */

// Dynamic API URL - matches AuthContext logic
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

export interface FunctionCallDetail {
  name: string;
  tokens: number;
}

export interface InputBreakdown {
  system_prompt_tokens: number;
  tools_tokens: number;
  history_tokens: number;
  user_message_tokens: number;
  files_tokens: number;
  tool_results_tokens?: number;  // Tokens từ kết quả của các tool calls
}

export interface ImageGenerationTokens {
  prompt_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface TokenBreakdown {
  input_breakdown?: InputBreakdown;  // Chi tiết input tokens
  text_tokens: number;
  function_call_tokens: number;
  function_calls_detail?: FunctionCallDetail[];
  image_generation?: ImageGenerationTokens;  // Tokens cho việc tạo ảnh
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  breakdown?: TokenBreakdown;
}

export interface AgentMessage {
  id: number;
  role: 'user' | 'agent' | 'system';
  message: string;
  function_calls: any[];
  created_at: string;
  token_usage?: TokenUsage;
}

export interface AgentPostImage {
  id: number;
  url: string;
  order: number;
}

export interface GenerationStrategy {
  layout?: 'single' | 'two_square' | 'one_large_two_small' | 'four_square' | 'two_large_three_small' | 'grid';
  image_count?: number;
  page_context?: string;
}

export interface TargetAccount {
  id: number;
  name: string;
  platform: string;
  profile_picture_url: string;
}

export interface AgentPost {
  id: number;
  content: string;
  full_content: string;
  hashtags: string[];
  image_url: string | null;  // Backward compatible - first image
  images: AgentPostImage[];  // All images
  status: string;
  target_account?: TargetAccount | null;  // Page được gắn với bài đăng
  agent_reasoning?: string;
  generation_strategy?: GenerationStrategy;
  created_at: string;
  completed_at: string | null;
}

export interface ChatResponse {
  agent_response: string;
  conversation_id: number;
  function_calls: any[];
  token_usage?: TokenUsage;
}

// Streaming event types
export interface StreamProgressEvent {
  type: 'progress';
  step: string;
  message: string;
}

export interface StreamFunctionCallEvent {
  type: 'function_call';
  name: string;
  display_name: string;
  args: Record<string, any>;
  current: number;
  total: number;
  message: string;
}

export interface StreamFunctionResultEvent {
  type: 'function_result';
  name: string;
  success: boolean;
  message: string;
}

export interface StreamDoneEvent {
  type: 'done';
  response: string;
  conversation_id: number;
  function_calls: any[];
  token_usage?: TokenUsage;
}

export interface StreamErrorEvent {
  type: 'error';
  message: string;
}

export type StreamEvent =
  | StreamProgressEvent
  | StreamFunctionCallEvent
  | StreamFunctionResultEvent
  | StreamDoneEvent
  | StreamErrorEvent;

class AgentService {
  private getAuthHeaders(): HeadersInit {
    // Get access_token from tokens object (matches AuthContext)
    const tokensStr = localStorage.getItem('tokens');
    const tokens = tokensStr ? JSON.parse(tokensStr) : null;
    const accessToken = tokens?.access_token || '';

    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    };
  }

  /**
   * Send chat message to agent
   */
  async sendMessage(message: string): Promise<ChatResponse> {
    const response = await fetch(`${getApiUrl()}/api/agent/chat`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error('Không thể gửi tin nhắn');
    }

    return response.json();
  }

  /**
   * Send chat message with streaming progress updates
   * @param message - Tin nhắn gửi đến agent
   * @param files - Các file đính kèm (ảnh, tài liệu)
   * @param onEvent - Callback được gọi khi nhận event mới
   */
  async sendMessageStream(
    message: string,
    files: File[] = [],
    onEvent: (event: StreamEvent) => void
  ): Promise<void> {
    // Use FormData if there are files, otherwise use JSON
    let response: Response;

    if (files.length > 0) {
      const formData = new FormData();
      formData.append('message', message);
      files.forEach((file, index) => {
        formData.append(`file_${index}`, file);
      });

      // Get auth token
      const tokensStr = localStorage.getItem('tokens');
      const tokens = tokensStr ? JSON.parse(tokensStr) : null;
      const accessToken = tokens?.access_token || '';

      response = await fetch(`${getApiUrl()}/api/agent/chat/stream`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          // Don't set Content-Type - browser will set it with boundary for FormData
        },
        body: formData,
      });
    } else {
      response = await fetch(`${getApiUrl()}/api/agent/chat/stream`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ message }),
      });
    }

    if (!response.ok) {
      throw new Error('Không thể gửi tin nhắn');
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Không thể đọc response stream');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data as StreamEvent);
          } catch (e) {
            console.error('Error parsing SSE event:', e);
          }
        }
      }
    }
  }

  /**
   * Get conversation history
   */
  async getConversationHistory(limit: number = 50): Promise<AgentMessage[]> {
    const response = await fetch(`${getApiUrl()}/api/agent/chat/history?limit=${limit}`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch conversation history');
    }

    return response.json();
  }

  /**
   * Clear conversation history
   */
  async clearHistory(): Promise<void> {
    const response = await fetch(`${getApiUrl()}/api/agent/chat/history`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to clear history');
    }
  }

  /**
   * Get agent posts
   */
  async getPosts(limit: number = 20): Promise<AgentPost[]> {
    const response = await fetch(`${getApiUrl()}/api/agent/posts?limit=${limit}`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch posts');
    }

    return response.json();
  }

  /**
   * Get post detail
   */
  async getPostDetail(postId: number): Promise<any> {
    const response = await fetch(`${getApiUrl()}/api/agent/posts/${postId}`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch post detail');
    }

    return response.json();
  }

  /**
   * Delete post
   */
  async deletePost(postId: number): Promise<void> {
    const response = await fetch(`${getApiUrl()}/api/agent/posts/${postId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to delete post');
    }
  }

  /**
   * Update post (quick edit)
   */
  async updatePost(postId: number, data: {
    content?: string;
    full_content?: string;
    hashtags?: string[];
  }): Promise<AgentPost> {
    const response = await fetch(`${getApiUrl()}/api/agent/posts/${postId}`, {
      method: 'PATCH',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to update post');
    }

    const result = await response.json();
    return result.post;
  }

  /**
   * Get agent stats
   */
  async getStats(): Promise<any> {
    const response = await fetch(`${getApiUrl()}/api/agent/stats`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch stats');
    }

    return response.json();
  }

  /**
   * Get agent settings
   */
  async getSettings(): Promise<AgentSettings> {
    const response = await fetch(`${getApiUrl()}/api/agent/settings`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch settings');
    }

    return response.json();
  }

  /**
   * Update agent settings
   */
  async updateSettings(data: Partial<AgentSettings>): Promise<any> {
    const response = await fetch(`${getApiUrl()}/api/agent/settings`, {
      method: 'PUT',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to update settings');
    }

    return response.json();
  }

  /**
   * Upload logo
   */
  async uploadLogo(file: File): Promise<{ id: number; url: string }> {
    const tokensStr = localStorage.getItem('tokens');
    const tokens = tokensStr ? JSON.parse(tokensStr) : null;
    const accessToken = tokens?.access_token || '';

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${getApiUrl()}/api/agent/settings/logo`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to upload logo');
    }

    const result = await response.json();
    return result.logo;
  }
}

export interface AgentSettings {
  logo_id: number | null;
  logo_url: string | null;
  logo_position: 'top_left' | 'top_right' | 'bottom_left' | 'bottom_right' | 'center';
  logo_size: number;
  auto_add_logo: boolean;
  hotline: string;
  website: string;
  auto_add_hotline: boolean;
  slogan: string;
  brand_colors: string[];
  default_tone: 'professional' | 'casual' | 'friendly' | 'funny' | 'formal';
  default_word_count: number;
}

export const agentService = new AgentService();
