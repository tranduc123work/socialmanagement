/**
 * Task Context - Manages async AI tasks across the application
 * Provides task tracking, polling, and notifications
 */
import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { AITaskService, TaskStatusResponse } from '../services/aiTaskService';
import { toast } from 'sonner';
import { useAuth } from './AuthContext';

interface Task extends TaskStatusResponse {
  // Additional UI state
  isPolling?: boolean;
}

interface TaskContextType {
  tasks: Map<string, Task>;
  activeTasksCount: number;
  addTask: (taskId: string, taskType: 'content' | 'image' | 'schedule') => void;
  removeTask: (taskId: string) => void;
  getTask: (taskId: string) => Task | undefined;
  startPolling: (taskId: string) => void;
  stopPolling: (taskId: string) => void;
  clearCompletedTasks: () => void;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export function TaskProvider({ children }: { children: React.ReactNode }) {
  const { tokens } = useAuth();
  const [tasks, setTasks] = useState<Map<string, Task>>(new Map());
  const pollingIntervals = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const notificationShown = useRef<Set<string>>(new Set());

  // Calculate active tasks count (pending or processing)
  const activeTasksCount = Array.from(tasks.values()).filter(
    task => task.status === 'pending' || task.status === 'processing'
  ).length;

  /**
   * Request browser notification permission
   */
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  /**
   * Show browser notification
   */
  const showNotification = useCallback((task: Task) => {
    if (notificationShown.current.has(task.task_id)) {
      return;
    }

    notificationShown.current.add(task.task_id);

    // Show toast notification
    if (task.status === 'completed') {
      toast.success(`${getTaskTypeLabel(task.task_type)} hoàn thành!`, {
        description: `Tác vụ đã hoàn thành sau ${task.duration_seconds?.toFixed(1)}s`,
        duration: 5000,
      });
    } else if (task.status === 'failed') {
      toast.error(`${getTaskTypeLabel(task.task_type)} thất bại`, {
        description: task.error_message || 'Đã xảy ra lỗi',
        duration: 5000,
      });
    }

    // Show browser notification if permitted
    if ('Notification' in window && Notification.permission === 'granted') {
      const title = task.status === 'completed'
        ? `✓ ${getTaskTypeLabel(task.task_type)} hoàn thành`
        : `✗ ${getTaskTypeLabel(task.task_type)} thất bại`;

      const body = task.status === 'completed'
        ? `Tác vụ đã hoàn thành sau ${task.duration_seconds?.toFixed(1)}s`
        : task.error_message || 'Đã xảy ra lỗi';

      new Notification(title, {
        body,
        icon: '/logo.png',
        tag: task.task_id,
      });
    }
  }, []);

  /**
   * Poll task status
   */
  const pollTask = useCallback(async (taskId: string) => {
    if (!tokens?.access_token) {
      console.error('No access token available for polling');
      return;
    }

    try {
      const status = await AITaskService.getTaskStatus(tokens.access_token, taskId);

      setTasks(prev => {
        const updated = new Map(prev);
        updated.set(taskId, { ...status, isPolling: true });
        return updated;
      });

      // If task is complete or failed, stop polling and show notification
      if (status.status === 'completed' || status.status === 'failed') {
        // Stop polling - clear interval directly
        const interval = pollingIntervals.current.get(taskId);
        if (interval) {
          clearInterval(interval);
          pollingIntervals.current.delete(taskId);
        }

        setTasks(prev => {
          const updated = new Map(prev);
          const task = updated.get(taskId);
          if (task) {
            updated.set(taskId, { ...task, isPolling: false });
          }
          return updated;
        });

        showNotification(status);
      }
    } catch (error) {
      console.error(`Error polling task ${taskId}:`, error);
      // Continue polling even on error
    }
  }, [tokens, showNotification]);

  /**
   * Start polling a task
   */
  const startPolling = useCallback((taskId: string) => {
    // Don't start if already polling
    if (pollingIntervals.current.has(taskId)) {
      return;
    }

    // Poll immediately
    pollTask(taskId);

    // Then poll every 3 seconds
    const interval = setInterval(() => {
      pollTask(taskId);
    }, 3000);

    pollingIntervals.current.set(taskId, interval);
  }, [pollTask]);

  /**
   * Stop polling a task
   */
  const stopPolling = useCallback((taskId: string) => {
    const interval = pollingIntervals.current.get(taskId);
    if (interval) {
      clearInterval(interval);
      pollingIntervals.current.delete(taskId);
    }

    setTasks(prev => {
      const updated = new Map(prev);
      const task = updated.get(taskId);
      if (task) {
        updated.set(taskId, { ...task, isPolling: false });
      }
      return updated;
    });
  }, []);

  /**
   * Add a new task and start polling
   */
  const addTask = useCallback((taskId: string, taskType: 'content' | 'image' | 'schedule') => {
    const newTask: Task = {
      task_id: taskId,
      task_type: taskType,
      status: 'pending',
      progress: 0,
      created_at: new Date().toISOString(),
      isPolling: true,
    };

    setTasks(prev => {
      const updated = new Map(prev);
      updated.set(taskId, newTask);
      return updated;
    });

    // Start polling
    startPolling(taskId);

    // Show toast notification
    toast.info(`Đã bắt đầu ${getTaskTypeLabel(taskType)}`, {
      description: 'Bạn có thể tiếp tục làm việc trong khi AI đang xử lý',
      duration: 3000,
    });
  }, [startPolling]);

  /**
   * Remove task from list
   */
  const removeTask = useCallback((taskId: string) => {
    stopPolling(taskId);
    setTasks(prev => {
      const updated = new Map(prev);
      updated.delete(taskId);
      return updated;
    });
    notificationShown.current.delete(taskId);
  }, [stopPolling]);

  /**
   * Get task by ID
   */
  const getTask = useCallback((taskId: string) => {
    return tasks.get(taskId);
  }, [tasks]);

  /**
   * Clear all completed tasks
   */
  const clearCompletedTasks = useCallback(() => {
    setTasks(prev => {
      const updated = new Map(prev);
      Array.from(updated.entries()).forEach(([taskId, task]) => {
        if (task.status === 'completed' || task.status === 'failed') {
          stopPolling(taskId);
          updated.delete(taskId);
          notificationShown.current.delete(taskId);
        }
      });
      return updated;
    });
  }, [stopPolling]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      // Stop all polling intervals
      pollingIntervals.current.forEach(interval => clearInterval(interval));
      pollingIntervals.current.clear();
    };
  }, []);

  const value: TaskContextType = {
    tasks,
    activeTasksCount,
    addTask,
    removeTask,
    getTask,
    startPolling,
    stopPolling,
    clearCompletedTasks,
  };

  return <TaskContext.Provider value={value}>{children}</TaskContext.Provider>;
}

/**
 * Hook to use task context
 */
export function useTasks() {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error('useTasks must be used within TaskProvider');
  }
  return context;
}

/**
 * Helper to get task type label in Vietnamese
 */
function getTaskTypeLabel(taskType: string): string {
  switch (taskType) {
    case 'content':
      return 'Tạo nội dung';
    case 'image':
      return 'Tạo hình ảnh';
    case 'schedule':
      return 'Tạo lịch đăng bài';
    default:
      return 'Tác vụ AI';
  }
}
