/**
 * Task Notification Badge - Displays active AI tasks with progress
 */
import React, { useState } from 'react';
import { useTasks } from '../contexts/TaskContext';
import { Bell, Loader2, CheckCircle2, XCircle, X, Trash2 } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { ScrollArea } from './ui/scroll-area';

export function TaskNotificationBadge() {
  const { tasks, activeTasksCount, removeTask, clearCompletedTasks } = useTasks();
  const [isOpen, setIsOpen] = useState(false);

  const tasksArray = Array.from(tasks.values()).sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const getTaskIcon = (status: string) => {
    switch (status) {
      case 'pending':
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getTaskTypeLabel = (taskType: string) => {
    switch (taskType) {
      case 'content':
        return 'Tạo nội dung';
      case 'image':
        return 'Tạo hình ảnh';
      case 'schedule':
        return 'Tạo lịch';
      default:
        return 'Tác vụ AI';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Đang chờ';
      case 'processing':
        return 'Đang xử lý';
      case 'completed':
        return 'Hoàn thành';
      case 'failed':
        return 'Thất bại';
      default:
        return status;
    }
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="relative"
        >
          <Bell className="h-5 w-5" />
          {activeTasksCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
            >
              {activeTasksCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-96">
        <div className="flex items-center justify-between p-3 border-b">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            <span className="font-semibold">Tác vụ AI</span>
            {activeTasksCount > 0 && (
              <Badge variant="secondary" className="ml-1">
                {activeTasksCount} đang chạy
              </Badge>
            )}
          </div>
          {tasks.size > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearCompletedTasks}
              className="h-8 text-xs"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Xóa hoàn thành
            </Button>
          )}
        </div>

        <ScrollArea className="max-h-96">
          {tasksArray.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              <Bell className="h-12 w-12 mx-auto mb-2 opacity-20" />
              <p>Không có tác vụ nào</p>
              <p className="text-xs mt-1">Các tác vụ AI sẽ hiển thị ở đây</p>
            </div>
          ) : (
            <div className="divide-y">
              {tasksArray.map((task) => (
                <div key={task.task_id} className="p-3 hover:bg-muted/50 transition-colors">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {getTaskIcon(task.status)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {getTaskTypeLabel(task.task_type)}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge
                            variant="secondary"
                            className={`text-xs ${getStatusColor(task.status)}`}
                          >
                            {getStatusLabel(task.status)}
                          </Badge>
                          {task.duration_seconds && (
                            <span className="text-xs text-muted-foreground">
                              {task.duration_seconds.toFixed(1)}s
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 flex-shrink-0"
                      onClick={() => removeTask(task.task_id)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>

                  {(task.status === 'pending' || task.status === 'processing') && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Tiến độ</span>
                        <span>{task.progress}%</span>
                      </div>
                      <Progress value={task.progress} className="h-1.5" />
                    </div>
                  )}

                  {task.status === 'failed' && task.error_message && (
                    <p className="text-xs text-red-600 mt-2 line-clamp-2">
                      {task.error_message}
                    </p>
                  )}

                  {task.status === 'completed' && task.result && (
                    <p className="text-xs text-green-600 mt-2">
                      ✓ Tác vụ hoàn thành thành công
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
