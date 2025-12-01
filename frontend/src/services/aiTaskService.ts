/**
 * AI Task Service - Handles async AI generation tasks
 */

// Dynamic API URL - matches the same logic as MediaLibrary
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

export interface TaskSubmitResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  task_type: 'content' | 'image' | 'schedule';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: any;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
}

export interface TaskStatsResponse {
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  avg_duration_content?: number;
  avg_duration_image?: number;
  avg_duration_schedule?: number;
  recent_tasks: Array<{
    task_id: string;
    task_type: string;
    status: string;
    duration_seconds?: number;
    created_at: string;
    completed_at?: string;
  }>;
}

export class AITaskService {
  private static getHeaders(token: string): HeadersInit {
    return {
      'Authorization': `Bearer ${token}`
    };
  }

  /**
   * Submit content generation task
   */
  static async submitContentTask(
    token: string,
    params: {
      prompt: string;
      tone?: string;
      include_hashtags?: boolean;
      include_emoji?: boolean;
      language?: string;
    }
  ): Promise<TaskSubmitResponse> {
    const formData = new FormData();
    formData.append('prompt', params.prompt);
    formData.append('tone', params.tone || 'professional');
    formData.append('include_hashtags', String(params.include_hashtags ?? true));
    formData.append('include_emoji', String(params.include_emoji ?? true));
    formData.append('language', params.language || 'vi');

    const response = await fetch(`${getApiUrl()}/api/ai/tasks/content/submit`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Failed to submit content task: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Submit image generation task
   */
  static async submitImageTask(
    token: string,
    params: {
      prompt: string;
      size: string;
      creativity: string;
      reference_images?: File[];
    }
  ): Promise<TaskSubmitResponse> {
    const formData = new FormData();
    formData.append('prompt', params.prompt);
    formData.append('size', params.size);
    formData.append('creativity', params.creativity);

    if (params.reference_images) {
      params.reference_images.forEach((file) => {
        formData.append('reference_images', file);
      });
    }

    const response = await fetch(`${getApiUrl()}/api/ai/tasks/image/submit`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Failed to submit image task: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Submit schedule generation task
   */
  static async submitScheduleTask(
    token: string,
    params: {
      business_type: string;
      goals: string;
      start_date: string;
      duration?: string;
      posts_per_day?: number;
      language?: string;
    }
  ): Promise<TaskSubmitResponse> {
    const formData = new FormData();
    formData.append('business_type', params.business_type);
    formData.append('goals', params.goals);
    formData.append('start_date', params.start_date);
    formData.append('duration', params.duration || '1_week');
    formData.append('posts_per_day', String(params.posts_per_day || 2));
    formData.append('language', params.language || 'vi');

    const response = await fetch(`${getApiUrl()}/api/ai/tasks/schedule/submit`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Failed to submit schedule task: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get task status (for polling)
   */
  static async getTaskStatus(token: string, taskId: string): Promise<TaskStatusResponse> {
    const response = await fetch(`${getApiUrl()}/api/ai/tasks/${taskId}/status`, {
      headers: this.getHeaders(token)
    });

    if (!response.ok) {
      throw new Error(`Failed to get task status: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get task statistics
   */
  static async getTaskStats(token: string): Promise<TaskStatsResponse> {
    const response = await fetch(`${getApiUrl()}/api/ai/tasks/stats`, {
      headers: this.getHeaders(token)
    });

    if (!response.ok) {
      throw new Error(`Failed to get task stats: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Cancel/delete task
   */
  static async cancelTask(token: string, taskId: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${getApiUrl()}/api/ai/tasks/${taskId}`, {
      method: 'DELETE',
      headers: this.getHeaders(token)
    });

    if (!response.ok) {
      throw new Error(`Failed to cancel task: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Poll task until completion
   * @param token Authentication token
   * @param taskId Task ID to poll
   * @param onProgress Callback for progress updates
   * @param interval Polling interval in milliseconds (default: 3000)
   */
  static async pollTaskUntilComplete(
    token: string,
    taskId: string,
    onProgress?: (status: TaskStatusResponse) => void,
    interval: number = 3000
  ): Promise<TaskStatusResponse> {
    return new Promise((resolve, reject) => {
      const pollInterval = setInterval(async () => {
        try {
          const status = await this.getTaskStatus(token, taskId);

          // Call progress callback
          if (onProgress) {
            onProgress(status);
          }

          // Check if task is complete
          if (status.status === 'completed') {
            clearInterval(pollInterval);
            resolve(status);
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            reject(new Error(status.error_message || 'Task failed'));
          }
        } catch (error) {
          clearInterval(pollInterval);
          reject(error);
        }
      }, interval);
    });
  }
}
