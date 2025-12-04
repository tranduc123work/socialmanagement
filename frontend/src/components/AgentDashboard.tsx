'use client';

import { useState, useRef } from 'react';
import { MessageSquare, Images } from 'lucide-react';
import { AgentChat } from './AgentChat';
import { AgentPostsGallery } from './AgentPostsGallery';

type AgentTab = 'chat' | 'posts';

export function AgentDashboard() {
  const [activeTab, setActiveTab] = useState<AgentTab>('chat');
  const postsGalleryRef = useRef<{ refresh: () => void }>(null);
  const [pendingAgentMessage, setPendingAgentMessage] = useState<string | null>(null);

  const handlePostCreated = () => {
    // Trigger posts gallery refresh when agent creates a post
    postsGalleryRef.current?.refresh();
  };

  const handleRequestAgentEdit = (message: string) => {
    // Set the message to be sent to agent and switch to chat tab (on mobile)
    setPendingAgentMessage(message);
    setActiveTab('chat');
  };

  return (
    <div className="flex h-full w-full bg-gray-50">
      {/* Main Content - Split View */}
      <div className="flex-1 flex h-full overflow-hidden">
        {/* Left Panel - Chat (Always Visible on Desktop) */}
        <div className="hidden lg:flex lg:w-1/2 h-full border-r border-gray-200">
          <AgentChat
            onPostCreated={handlePostCreated}
            initialMessage={pendingAgentMessage}
            onInitialMessageSent={() => setPendingAgentMessage(null)}
          />
        </div>

        {/* Right Panel - Posts Gallery (Always Visible on Desktop) */}
        <div className="hidden lg:flex lg:w-1/2 h-full overflow-hidden">
          <AgentPostsGallery ref={postsGalleryRef} onRequestAgentEdit={handleRequestAgentEdit} />
        </div>

        {/* Mobile View - Tabs */}
        <div className="flex lg:hidden flex-1 flex-col h-full overflow-hidden">
          {/* Mobile Tabs */}
          <div className="bg-white border-b border-gray-200 flex shrink-0">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 transition-colors ${
                activeTab === 'chat'
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <MessageSquare className="w-5 h-5" />
              <span>Chat</span>
            </button>
            <button
              onClick={() => setActiveTab('posts')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 transition-colors ${
                activeTab === 'posts'
                  ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Images className="w-5 h-5" />
              <span>Bài đăng</span>
            </button>
          </div>

          {/* Mobile Content */}
          <div className="flex-1 h-full overflow-hidden">
            {activeTab === 'chat' ? (
              <AgentChat
                onPostCreated={handlePostCreated}
                initialMessage={pendingAgentMessage}
                onInitialMessageSent={() => setPendingAgentMessage(null)}
              />
            ) : (
              <AgentPostsGallery ref={postsGalleryRef} onRequestAgentEdit={handleRequestAgentEdit} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
