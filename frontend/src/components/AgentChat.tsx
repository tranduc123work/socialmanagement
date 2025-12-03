'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Trash2, Bot, User, ChevronDown, ChevronUp, Zap, CheckCircle, AlertCircle } from 'lucide-react';
import { agentService, AgentMessage, StreamEvent } from '@/services/agentService';

interface AgentChatProps {
  onPostCreated?: () => void;
}

const CACHE_KEY = 'agent_chat_cache';
const CACHE_EXPIRY_KEY = 'agent_chat_cache_expiry';
const CACHE_DURATION_MS = 24 * 60 * 60 * 1000; // 24 hours

// Cache utilities
const getCachedMessages = (): AgentMessage[] | null => {
  try {
    const expiry = localStorage.getItem(CACHE_EXPIRY_KEY);
    if (expiry && Date.now() > parseInt(expiry)) {
      // Cache expired
      localStorage.removeItem(CACHE_KEY);
      localStorage.removeItem(CACHE_EXPIRY_KEY);
      return null;
    }
    const cached = localStorage.getItem(CACHE_KEY);
    return cached ? JSON.parse(cached) : null;
  } catch {
    return null;
  }
};

const setCachedMessages = (messages: AgentMessage[]) => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(messages));
    localStorage.setItem(CACHE_EXPIRY_KEY, (Date.now() + CACHE_DURATION_MS).toString());
  } catch (e) {
    console.warn('Failed to cache messages:', e);
  }
};

const clearMessageCache = () => {
  localStorage.removeItem(CACHE_KEY);
  localStorage.removeItem(CACHE_EXPIRY_KEY);
};

// Progress step interface
interface ProgressStep {
  name: string;
  displayName: string;
  status: 'pending' | 'running' | 'success' | 'error';
  message?: string;
}

export function AgentChat({ onPostCreated }: AgentChatProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingHistory, setIsFetchingHistory] = useState(true);
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [currentProgressMessage, setCurrentProgressMessage] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const toggleMessageExpansion = (messageId: number) => {
    setExpandedMessages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  // Load from cache first, then sync with API
  useEffect(() => {
    // Step 1: Load from cache immediately (instant UI)
    const cached = getCachedMessages();
    const cacheCount = cached?.length || 0;

    if (cached && cacheCount > 0) {
      setMessages(cached);
      setIsFetchingHistory(false);
    }

    // Step 2: Sync with API in background (pass cache count for comparison)
    loadHistory(cacheCount);
  }, []);

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadHistory = async (cacheCount: number = 0) => {
    try {
      if (cacheCount === 0) {
        setIsFetchingHistory(true);
      }
      const history = await agentService.getConversationHistory();
      const cached = getCachedMessages();

      // Tạo map token_usage từ cache (vì API không trả về token_usage)
      const tokenUsageMap = new Map<number, AgentMessage['token_usage']>();
      if (cached) {
        cached.forEach(msg => {
          if (msg.token_usage) {
            tokenUsageMap.set(msg.id, msg.token_usage);
          }
        });
      }

      // Merge token_usage từ cache vào history
      const mergedHistory = history.map(msg => ({
        ...msg,
        token_usage: msg.token_usage || tokenUsageMap.get(msg.id),
      }));

      // Chỉ cập nhật nếu:
      // 1. API trả về NHIỀU HƠN cache (có tin nhắn mới từ server)
      // 2. Hoặc không có cache (lần đầu load)
      // KHÔNG ghi đè nếu API trả về ít hơn cache (tránh mất tin nhắn)
      if (history.length >= cacheCount) {
        setMessages(mergedHistory);
        setCachedMessages(mergedHistory);
      }
      // Nếu API ít hơn cache -> giữ nguyên cache (đã load ở useEffect)
    } catch (error) {
      console.error('Failed to load history:', error);
      // Nếu lỗi API -> giữ cache hiện tại
    } finally {
      setIsFetchingHistory(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);
    setProgressSteps([]);
    setCurrentProgressMessage('Đang phân tích yêu cầu...');

    // Add user message to UI immediately
    const tempUserMessage: AgentMessage = {
      id: Date.now(),
      role: 'user',
      message: userMessage,
      function_calls: [],
      created_at: new Date().toISOString(),
    };
    setMessages(prev => {
      const updated = [...prev, tempUserMessage];
      setCachedMessages(updated);
      return updated;
    });

    try {
      await agentService.sendMessageStream(userMessage, (event: StreamEvent) => {
        switch (event.type) {
          case 'progress':
            setCurrentProgressMessage(event.message);
            break;

          case 'function_call':
            setCurrentProgressMessage(event.message);
            setProgressSteps(prev => {
              // Check if step already exists
              const existing = prev.find(s => s.name === event.name);
              if (existing) {
                return prev.map(s =>
                  s.name === event.name ? { ...s, status: 'running' as const } : s
                );
              }
              return [
                ...prev,
                {
                  name: event.name,
                  displayName: event.display_name,
                  status: 'running' as const,
                  message: event.message,
                },
              ];
            });
            break;

          case 'function_result':
            setProgressSteps(prev =>
              prev.map(s =>
                s.name === event.name
                  ? {
                      ...s,
                      status: event.success ? ('success' as const) : ('error' as const),
                      message: event.message,
                    }
                  : s
              )
            );
            break;

          case 'done':
            // Add agent response
            const agentMessage: AgentMessage = {
              id: event.conversation_id,
              role: 'agent',
              message: event.response,
              function_calls: event.function_calls,
              created_at: new Date().toISOString(),
              token_usage: event.token_usage,
            };
            setMessages(prev => {
              const updated = [...prev, agentMessage];
              setCachedMessages(updated);
              return updated;
            });

            // Check if agent created a post, trigger refresh
            const createdPost = event.function_calls?.some(
              (fc: any) => fc.name === 'save_agent_post'
            );
            if (createdPost && onPostCreated) {
              setTimeout(() => onPostCreated(), 1000);
            }
            break;

          case 'error':
            const errorMessage: AgentMessage = {
              id: Date.now(),
              role: 'system',
              message: `Lỗi: ${event.message}`,
              function_calls: [],
              created_at: new Date().toISOString(),
            };
            setMessages(prev => [...prev, errorMessage]);
            break;
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: AgentMessage = {
        id: Date.now(),
        role: 'system',
        message: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.',
        function_calls: [],
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setProgressSteps([]);
      setCurrentProgressMessage('');
    }
  };

  const handleClearHistory = async () => {
    if (!confirm('Bạn có chắc muốn xóa toàn bộ lịch sử trò chuyện?')) return;

    try {
      await agentService.clearHistory();
      setMessages([]);
      // Clear cache as well
      clearMessageCache();
    } catch (error) {
      console.error('Failed to clear history:', error);
      alert('Không thể xóa lịch sử. Vui lòng thử lại.');
    }
  };

  const renderMessage = (msg: AgentMessage) => {
    const isUser = msg.role === 'user';
    const isSystem = msg.role === 'system';
    const isLongMessage = msg.message.length > 500;
    const isExpanded = expandedMessages.has(msg.id);
    const shouldTruncate = isLongMessage && !isExpanded;
    const displayMessage = shouldTruncate
      ? msg.message.substring(0, 500) + '...'
      : msg.message;

    return (
      <div
        key={msg.id}
        className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-4`}
      >
        {/* Avatar */}
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser
              ? 'bg-blue-500'
              : isSystem
              ? 'bg-gray-400'
              : 'bg-gradient-to-br from-purple-500 to-pink-500'
          }`}
        >
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </div>

        {/* Message */}
        <div
          className={`max-w-[70%] rounded-2xl px-4 py-2 ${
            isUser
              ? 'bg-blue-500 text-white'
              : isSystem
              ? 'bg-gray-100 text-gray-700'
              : 'bg-white border border-gray-200 text-gray-800'
          }`}
        >
          <p className="whitespace-pre-wrap break-words">{displayMessage}</p>

          {/* Expand/Collapse button for long messages */}
          {isLongMessage && (
            <button
              onClick={() => toggleMessageExpansion(msg.id)}
              className={`mt-2 flex items-center gap-1 text-xs font-medium transition-colors ${
                isUser
                  ? 'text-white/80 hover:text-white'
                  : 'text-blue-600 hover:text-blue-700'
              }`}
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-3 h-3" />
                  Thu gọn
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" />
                  Xem thêm
                </>
              )}
            </button>
          )}

          {/* Show function calls if any */}
          {msg.function_calls && msg.function_calls.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-200/20">
              <p className="text-xs opacity-70 mb-1">Đã thực hiện:</p>
              {msg.function_calls.map((fc, idx) => (
                <span
                  key={idx}
                  className="inline-block text-xs bg-black/10 rounded-full px-2 py-0.5 mr-1"
                >
                  {fc.name}
                </span>
              ))}
            </div>
          )}

          {/* Footer: timestamp and token usage */}
          <div className="flex items-center gap-2 mt-1">
            <p className="text-xs opacity-50">
              {new Date(msg.created_at).toLocaleTimeString('vi-VN')}
            </p>
            {/* Show token usage for agent messages */}
            {msg.role === 'agent' && msg.token_usage && (
              <div className="flex items-center gap-1 text-xs opacity-50">
                <Zap className="w-3 h-3" />
                <span>{msg.token_usage.total_tokens.toLocaleString()} tokens</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full w-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Chat với AI Agent</h2>
          <p className="text-sm text-gray-500">
            Hỏi Agent về hệ thống hoặc yêu cầu tạo bài đăng
          </p>
        </div>
        <button
          onClick={handleClearHistory}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Xóa lịch sử"
        >
          <Trash2 className="w-4 h-4" />
          Xóa lịch sử
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isFetchingHistory ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">
              Xin chào! Tôi là AI Agent
            </h3>
            <p className="text-gray-500 max-w-md">
              Bạn có thể hỏi tôi về hệ thống, yêu cầu tạo bài đăng, phân tích lịch đăng,
              hoặc bất kỳ điều gì liên quan đến công việc marketing!
            </p>
            <div className="mt-6 space-y-2 text-sm text-gray-600">
              <p>💡 Ví dụ:</p>
              <p className="text-left">"Tạo bài đăng về sản phẩm mới"</p>
              <p className="text-left">"Kiểm tra lịch đăng của tôi"</p>
              <p className="text-left">"Có bao nhiêu bài đăng đã tạo?"</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map(renderMessage)}
            {isLoading && (
              <div className="flex gap-3 mb-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 min-w-[200px]">
                  {/* Current progress message */}
                  <div className="flex items-center gap-2 mb-2">
                    <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                    <span className="text-sm text-gray-700">{currentProgressMessage || 'Đang xử lý...'}</span>
                  </div>

                  {/* Progress steps */}
                  {progressSteps.length > 0 && (
                    <div className="space-y-1.5 pt-2 border-t border-gray-100">
                      {progressSteps.map((step, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-xs">
                          {step.status === 'running' && (
                            <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                          )}
                          {step.status === 'success' && (
                            <CheckCircle className="w-3 h-3 text-green-500" />
                          )}
                          {step.status === 'error' && (
                            <AlertCircle className="w-3 h-3 text-red-500" />
                          )}
                          {step.status === 'pending' && (
                            <div className="w-3 h-3 rounded-full border border-gray-300" />
                          )}
                          <span
                            className={`${
                              step.status === 'running'
                                ? 'text-blue-600 font-medium'
                                : step.status === 'success'
                                ? 'text-green-600'
                                : step.status === 'error'
                                ? 'text-red-600'
                                : 'text-gray-400'
                            }`}
                          >
                            {step.displayName}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4 shrink-0">
        <form onSubmit={handleSendMessage} className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={e => setInputMessage(e.target.value)}
            placeholder="Nhập tin nhắn..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
