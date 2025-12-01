/**
 * Agent API Service
 */

// Dynamic API URL - matches AuthContext logic
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    return `http://${hostname}:8000`;
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

export interface AgentMessage {
  id: number;
  role: 'user' | 'agent' | 'system';
  message: string;
  function_calls: any[];
  created_at: string;
}

export interface AgentPost {
  id: number;
  content: string;
  full_content: string;
  hashtags: string[];
  image_url: string | null;
  status: string;
  agent_reasoning?: string;
  generation_strategy?: any;
  created_at: string;
  completed_at: string | null;
}

export interface ChatResponse {
  agent_response: string;
  conversation_id: number;
  function_calls: any[];
}

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
      throw new Error('Failed to send message');
    }

    return response.json();
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
}

export const agentService = new AgentService();
