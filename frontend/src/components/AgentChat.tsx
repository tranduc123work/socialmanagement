'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Trash2, Bot, User, ChevronDown, ChevronUp, Zap, CheckCircle, AlertCircle, Paperclip, X, FileText, Image as ImageIcon } from 'lucide-react';
import { agentService, AgentMessage, StreamEvent } from '@/services/agentService';

interface AgentChatProps {
  onPostCreated?: () => void;
  initialMessage?: string | null;
  onInitialMessageSent?: () => void;
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

export function AgentChat({ onPostCreated, initialMessage, onInitialMessageSent }: AgentChatProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingHistory, setIsFetchingHistory] = useState(true);
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [currentProgressMessage, setCurrentProgressMessage] = useState<string>('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialMessageProcessedRef = useRef<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // File upload constants
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED_FILE_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'text/plain', 'text/csv', 'text/markdown',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ];

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

  // Handle initial message from parent (e.g., from "Nhờ Agent sửa" button)
  useEffect(() => {
    if (initialMessage && !isLoading && !isFetchingHistory && initialMessage !== initialMessageProcessedRef.current) {
      initialMessageProcessedRef.current = initialMessage;
      // Auto-send the message
      sendMessage(initialMessage);
      // Notify parent that message was sent
      if (onInitialMessageSent) {
        onInitialMessageSent();
      }
    }
  }, [initialMessage, isLoading, isFetchingHistory]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // File handling functions
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles: File[] = [];
    const errors: string[] = [];

    files.forEach(file => {
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: Vượt quá 10MB`);
      } else if (!ALLOWED_FILE_TYPES.includes(file.type)) {
        errors.push(`${file.name}: Loại file không được hỗ trợ`);
      } else {
        validFiles.push(file);
      }
    });

    if (errors.length > 0) {
      alert('Một số file không hợp lệ:\n' + errors.join('\n'));
    }

    setSelectedFiles(prev => [...prev, ...validFiles]);
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) {
      return <ImageIcon className="w-4 h-4" />;
    }
    return <FileText className="w-4 h-4" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
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

  // Core message sending logic (reusable)
  const sendMessage = async (messageText: string, files?: File[]) => {
    if ((!messageText.trim() && (!files || files.length === 0)) || isLoading) return;

    const userMessage = messageText.trim();
    const filesToSend = files || selectedFiles;
    setIsLoading(true);
    setProgressSteps([]);
    setCurrentProgressMessage(filesToSend.length > 0 ? 'Đang tải file lên...' : 'Đang phân tích yêu cầu...');

    // Add user message to UI immediately (include file names if any)
    const fileNames = filesToSend.length > 0
      ? `\n📎 ${filesToSend.map(f => f.name).join(', ')}`
      : '';
    const tempUserMessage: AgentMessage = {
      id: Date.now(),
      role: 'user',
      message: userMessage + fileNames,
      function_calls: [],
      created_at: new Date().toISOString(),
    };
    setMessages(prev => {
      const updated = [...prev, tempUserMessage];
      setCachedMessages(updated);
      return updated;
    });

    // Clear selected files immediately after adding to message
    setSelectedFiles([]);

    try {
      await agentService.sendMessageStream(userMessage, filesToSend, (event: StreamEvent) => {
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
            // Clear loading state ngay lập tức khi có lỗi
            setIsLoading(false);
            setProgressSteps([]);
            setCurrentProgressMessage('');
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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;
    const message = inputMessage.trim();
    setInputMessage('');
    await sendMessage(message);
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
          <div className="flex flex-col gap-1 mt-2">
            <p className="text-xs opacity-50">
              {new Date(msg.created_at).toLocaleTimeString('vi-VN')}
            </p>
            {/* Show detailed token usage for agent messages */}
            {msg.role === 'agent' && msg.token_usage && (
              <div className="flex flex-col gap-1">
                {/* Main token summary */}
                <div className="flex items-center gap-3 text-xs bg-gray-100 rounded px-2 py-1 w-fit">
                  <div className="flex items-center gap-1 text-blue-600">
                    <span className="font-medium">Input:</span>
                    <span>{msg.token_usage.input_tokens?.toLocaleString() || 0}</span>
                  </div>
                  <div className="flex items-center gap-1 text-green-600">
                    <span className="font-medium">Output:</span>
                    <span>{msg.token_usage.output_tokens?.toLocaleString() || 0}</span>
                  </div>
                  <div className="flex items-center gap-1 text-purple-600">
                    <Zap className="w-3 h-3" />
                    <span className="font-medium">Tổng:</span>
                    <span>{msg.token_usage.total_tokens?.toLocaleString() || 0}</span>
                  </div>
                </div>
                {/* Input breakdown - chi tiết thành phần input */}
                {msg.token_usage.breakdown?.input_breakdown && (
                  <div className="flex flex-col gap-0.5 text-[10px] text-gray-500 pl-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="opacity-70">Chi tiết input:</span>
                      {msg.token_usage.breakdown.input_breakdown.system_prompt_tokens > 0 && (
                        <span className="text-blue-500">
                          System Prompt: {msg.token_usage.breakdown.input_breakdown.system_prompt_tokens.toLocaleString()}
                        </span>
                      )}
                      {msg.token_usage.breakdown.input_breakdown.tools_tokens > 0 && (
                        <span className="text-indigo-500">
                          • Tools: {msg.token_usage.breakdown.input_breakdown.tools_tokens.toLocaleString()}
                        </span>
                      )}
                      {msg.token_usage.breakdown.input_breakdown.history_tokens > 0 && (
                        <span className="text-cyan-600">
                          • History: {msg.token_usage.breakdown.input_breakdown.history_tokens.toLocaleString()}
                        </span>
                      )}
                      {msg.token_usage.breakdown.input_breakdown.user_message_tokens > 0 && (
                        <span className="text-teal-600">
                          • Message: {msg.token_usage.breakdown.input_breakdown.user_message_tokens.toLocaleString()}
                        </span>
                      )}
                      {msg.token_usage.breakdown.input_breakdown.files_tokens > 0 && (
                        <span className="text-pink-500">
                          • Files: {msg.token_usage.breakdown.input_breakdown.files_tokens.toLocaleString()}
                        </span>
                      )}
                      {msg.token_usage.breakdown.input_breakdown.tool_results_tokens && msg.token_usage.breakdown.input_breakdown.tool_results_tokens > 0 && (
                        <span className="text-amber-600">
                          • Tool Results: {msg.token_usage.breakdown.input_breakdown.tool_results_tokens.toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                )}
                {/* Output breakdown if available */}
                {msg.token_usage.breakdown && (
                  <div className="flex flex-col gap-0.5 text-[10px] text-gray-500 pl-1">
                    <div className="flex items-center gap-2">
                      <span className="opacity-70">Chi tiết output:</span>
                      {msg.token_usage.breakdown.text_tokens > 0 && (
                        <span className="text-green-600">Trả lời: {msg.token_usage.breakdown.text_tokens.toLocaleString()}</span>
                      )}
                      {msg.token_usage.breakdown.function_call_tokens > 0 && (
                        <span className="text-orange-600">• Gọi tools: {msg.token_usage.breakdown.function_call_tokens.toLocaleString()}</span>
                      )}
                    </div>
                    {/* Chi tiết từng tool */}
                    {msg.token_usage?.breakdown?.function_calls_detail && msg.token_usage.breakdown.function_calls_detail.length > 0 && (
                      <div className="flex items-center gap-1 pl-2 text-gray-400">
                        <span>→</span>
                        {msg.token_usage.breakdown.function_calls_detail.map((fc, idx, arr) => (
                          <span key={idx} className="text-orange-500">
                            {fc.name}: {fc.tokens}
                            {idx < arr.length - 1 && ' •'}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {/* Image generation tokens - hiển thị nếu có */}
                {msg.token_usage?.breakdown?.image_generation && msg.token_usage.breakdown.image_generation.total_tokens > 0 && (
                  <div className="flex flex-col gap-0.5 text-[10px] text-gray-500 pl-1">
                    <div className="flex items-center gap-2">
                      <span className="opacity-70">🖼️ Tạo hình ảnh:</span>
                      <span className="text-rose-500">
                        Input: {msg.token_usage.breakdown.image_generation.prompt_tokens.toLocaleString()}
                      </span>
                      <span className="text-rose-600">
                        • Output: {msg.token_usage.breakdown.image_generation.output_tokens.toLocaleString()}
                      </span>
                      <span className="text-rose-700 font-medium">
                        • Tổng: {msg.token_usage.breakdown.image_generation.total_tokens.toLocaleString()}
                      </span>
                    </div>
                  </div>
                )}
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
          <h2 className="text-lg font-semibold text-gray-800">Chat với Fugu</h2>
          <p className="text-sm text-gray-500">
            Hỏi Fugu về hệ thống hoặc yêu cầu tạo bài đăng
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
              Xin chào! Tôi là Fugu
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
        {/* Selected files preview */}
        {selectedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2 text-sm"
              >
                {getFileIcon(file)}
                <span className="max-w-[150px] truncate">{file.name}</span>
                <span className="text-gray-400 text-xs">({formatFileSize(file.size)})</span>
                <button
                  onClick={() => removeFile(index)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSendMessage} className="flex gap-2">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,.pdf,.txt,.csv,.md,.doc,.docx"
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* File upload button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="px-3 py-2 text-gray-500 hover:text-blue-500 hover:bg-blue-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Đính kèm file (tối đa 10MB)"
          >
            <Paperclip className="w-5 h-5" />
          </button>

          <input
            type="text"
            value={inputMessage}
            onChange={e => setInputMessage(e.target.value)}
            placeholder={selectedFiles.length > 0 ? "Nhập câu hỏi về file..." : "Nhập tin nhắn..."}
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={isLoading || (!inputMessage.trim() && selectedFiles.length === 0)}
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
