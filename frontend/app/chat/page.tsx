'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { useAuth } from '@/hooks/useAuth';
import { conversationApi, feedbackApi, streamChat } from '@/lib/api';
import { Conversation, Message, Citation } from '@/types';

import {
  Plus, Send, LogOut, Trash2, MessageSquare, ChevronRight,
  ThumbsUp, ThumbsDown, Copy, RotateCcw, FileText, Clock,
  BookOpen, Shield, Settings, BarChart2, Loader2, Bot
} from 'lucide-react';

export default function ChatPage() {
  const { user, logout, isAdmin, loading } = useAuth();
  const router = useRouter();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, 1 | -1>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortStreamRef = useRef<(() => void) | null>(null);

  // Auth guard — wait until auth loading is done before redirecting
  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [user, loading, router]);

  // Load conversations
  useEffect(() => {
    if (!user) return;
    conversationApi.list().then((data) => {
      setConversations(data.conversations || []);
    }).catch(console.error);
  }, [user]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversation = async (id: string) => {
    setActiveConversationId(id);
    const data = await conversationApi.get(id);
    setMessages(data.messages || []);
  };

  const newConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setInput('');
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await conversationApi.delete(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) newConversation();
  };

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isStreaming) return;
    const userMessage = input.trim();
    setInput('');
    setIsStreaming(true);
    setStatusText('Thinking…');

    // Optimistically add user message
    const tempUserId = `temp-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: tempUserId,
        conversation_id: activeConversationId || '',
        role: 'user',
        content: userMessage,
        created_at: new Date().toISOString(),
      },
    ]);

    // Placeholder assistant message (streaming)
    const tempBotId = `bot-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: tempBotId,
        conversation_id: activeConversationId || '',
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        isStreaming: true,
        statusEvents: [],
      },
    ]);

    let accumulatedAnswer = '';
    let finalMsgId = tempBotId;
    let finalConvId = activeConversationId;

    const abort = streamChat(
      userMessage,
      activeConversationId,
      (type, data) => {
        if (type === 'metadata') {
          finalConvId = data.conversation_id;
          setActiveConversationId(data.conversation_id);
          // Update conversation list
          conversationApi.list().then((d) => setConversations(d.conversations || []));
        } else if (type === 'status') {
          setStatusText(data.message);
          setMessages((prev) => prev.map((m) =>
            m.id === tempBotId
              ? { ...m, statusEvents: [...(m.statusEvents || []), data.message] }
              : m
          ));
        } else if (type === 'token') {
          accumulatedAnswer += data.content;
          setMessages((prev) => prev.map((m) =>
            m.id === tempBotId ? { ...m, content: accumulatedAnswer } : m
          ));
        } else if (type === 'done') {
          finalMsgId = data.message_id;
          setMessages((prev) => prev.map((m) =>
            m.id === tempBotId
              ? {
                  ...m,
                  id: data.message_id,
                  content: accumulatedAnswer || data.answer || m.content,
                  isStreaming: false,
                  metadata: {
                    citations: data.citations,
                    confidence: data.confidence,
                    total_latency_ms: data.total_latency_ms,
                  },
                }
              : m
          ));
          setIsStreaming(false);
          setStatusText('');
        } else if (type === 'error') {
          setMessages((prev) => prev.map((m) =>
            m.id === tempBotId
              ? { ...m, content: data.message, isStreaming: false }
              : m
          ));
          setIsStreaming(false);
          setStatusText('');
        } else if (type === 'end') {
          setMessages((prev) => prev.map((m) =>
            m.id === tempBotId && m.isStreaming
              ? { ...m, content: m.content || 'The response ended before completion. Please try again.', isStreaming: false }
              : m
          ));
          setIsStreaming(false);
          setStatusText('');
        }
      },
      (err) => {
        console.error('Stream error:', err);
        setIsStreaming(false);
        setStatusText('');
        // On 401, session expired — log out and redirect to login
        if (err.message === 'HTTP 401') {
          logout();
          router.push('/login');
          return;
        }
        setMessages((prev) => prev.map((m) =>
          m.isStreaming
            ? { ...m, content: `Error: ${err.message}. Please try again.`, isStreaming: false }
            : m
        ));
      }
    );

    abortStreamRef.current = abort;
  }, [input, isStreaming, activeConversationId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const submitFeedback = async (messageId: string, rating: 1 | -1) => {
    await feedbackApi.submit(messageId, rating);
    setFeedbackGiven((prev) => ({ ...prev, [messageId]: rating }));
  };

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  // Show loading spinner while checking auth, then redirect if unauthenticated
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center glow-bg">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-10 h-10 text-violet-500 animate-spin" />
        <p className="text-zinc-400 text-sm">Loading WalchandGPT…</p>
      </div>
    </div>
  );
  if (!user) return null;

  const suggestedQuestions = [
    "What is the attendance policy?",
    "When is the semester exam?",
    "Who teaches DBMS in third year?",
    "What placement companies visited last year?",
    "What are the hostel rules?",
    "Tell me about the Computer Engineering department",
  ];

  return (
    <div className="flex h-screen bg-zinc-950 overflow-hidden">
      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside className="w-64 flex-shrink-0 glass border-r border-zinc-800/50 flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-zinc-800/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-sm">W</span>
            </div>
            <div>
              <h1 className="font-bold text-sm gradient-text">WalchandGPT</h1>
              <p className="text-[10px] text-zinc-500">AI College Assistant</p>
            </div>
          </div>
        </div>

        {/* New Chat button */}
        <div className="p-3">
          <button onClick={newConversation} className="btn-primary w-full text-xs py-2.5">
            <Plus size={14} />
            New Chat
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {conversations.length === 0 ? (
            <p className="text-zinc-600 text-xs text-center py-6 px-4">
              Start a conversation to see it here
            </p>
          ) : (
            <div className="flex flex-col gap-0.5">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className={`sidebar-item group justify-between ${
                    activeConversationId === conv.id ? 'active' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <MessageSquare size={13} className="flex-shrink-0" />
                    <span className="truncate text-xs">{conv.title}</span>
                  </div>
                  <button
                    onClick={(e) => deleteConversation(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all flex-shrink-0"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom nav */}
        <div className="p-2 border-t border-zinc-800/50 flex flex-col gap-1">
          {isAdmin && (
            <button
              onClick={() => router.push('/admin')}
              className="sidebar-item w-full text-left"
            >
              <BarChart2 size={14} />
              Admin Dashboard
            </button>
          )}
          <div className="sidebar-item justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <div className="avatar avatar-user flex-shrink-0">
                {user.name[0].toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-zinc-200 truncate">{user.name}</p>
                <p className="text-[10px] text-zinc-500 truncate capitalize">{user.role}</p>
              </div>
            </div>
            <button onClick={() => { logout(); router.push('/login'); }} className="text-zinc-600 hover:text-red-400 transition-colors">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="h-12 border-b border-zinc-800/50 flex items-center justify-between px-6 flex-shrink-0 glass">
          <div className="flex items-center gap-2">
            <Bot size={16} className="text-violet-400" />
            <span className="text-sm font-semibold text-zinc-200">
              {activeConversationId
                ? conversations.find((c) => c.id === activeConversationId)?.title || 'Conversation'
                : 'New Conversation'}
            </span>
          </div>
          {isStreaming && statusText && (
            <div className="flex items-center gap-2 text-xs text-violet-400">
              <Loader2 size={12} className="animate-spin" />
              {statusText}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-8">
              <div className="text-center animate-fade-in">
                <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-violet-500 via-indigo-500 to-pink-500 flex items-center justify-center mx-auto mb-6 shadow-2xl shadow-violet-500/20">
                  <span className="text-white font-bold text-3xl">W</span>
                </div>
                <h2 className="text-2xl font-bold mb-2 gradient-text">Ask WalchandGPT</h2>
                <p className="text-zinc-400 max-w-md">
                  Your AI-powered assistant for Walchand College of Engineering.
                  Ask about academics, faculty, timetables, exams, placements, and more.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 w-full max-w-3xl animate-fade-in">
                {suggestedQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); textareaRef.current?.focus(); }}
                    className="text-left bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-violet-500/30 rounded-xl p-4 text-sm text-zinc-300 hover:text-white transition-all duration-200 group"
                  >
                    <ChevronRight size={14} className="text-violet-400 mb-2 group-hover:translate-x-1 transition-transform" />
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto flex flex-col gap-6">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onFeedback={submitFeedback}
                  onCopy={copyMessage}
                  feedbackGiven={feedbackGiven[msg.id]}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input bar */}
        <div className="px-4 md:px-8 pb-6 flex-shrink-0">
          <div className="max-w-3xl mx-auto">
            <div className="glass rounded-2xl border border-zinc-700/50 focus-within:border-violet-500/50 transition-all duration-200 shadow-2xl">
              <div className="flex items-end gap-3 p-3">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask WalchandGPT anything about WCE…"
                  className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-600 resize-none outline-none max-h-32 leading-relaxed"
                  rows={1}
                  disabled={isStreaming}
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || isStreaming}
                  className="btn-primary flex-shrink-0 py-2 px-3 rounded-xl"
                  aria-label="Send message"
                >
                  {isStreaming ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Send size={16} />
                  )}
                </button>
              </div>
              <p className="px-4 pb-2 text-[10px] text-zinc-700">
                Press Enter to send · Shift+Enter for new line · WalchandGPT can make mistakes
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// ── Message Bubble Component ──────────────────────────────────────────────────
function MessageBubble({
  message,
  onFeedback,
  onCopy,
  feedbackGiven,
}: {
  message: Message;
  onFeedback: (id: string, r: 1 | -1) => void;
  onCopy: (c: string) => void;
  feedbackGiven?: 1 | -1;
}) {
  const isUser = message.role === 'user';
  const [citationsOpen, setCitationsOpen] = useState(false);
  const citations = message.metadata?.citations || [];

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`avatar flex-shrink-0 self-start mt-1 ${isUser ? 'avatar-user' : 'avatar-bot'}`}>
        {isUser ? (message as any).user?.name?.[0] || 'U' : '✦'}
      </div>

      <div className={`flex flex-col gap-2 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Status events (only for streaming bot messages) */}
        {!isUser && message.isStreaming && message.statusEvents && message.statusEvents.length > 0 && (
          <div className="flex flex-col gap-1">
            {message.statusEvents.map((evt, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-zinc-500">
                <Loader2 size={10} className="animate-spin text-violet-400" />
                {evt}
              </div>
            ))}
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-violet-600 text-white rounded-tr-sm'
              : 'bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-tl-sm'
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="message-content text-sm">
              {message.isStreaming && !message.content ? (
                <div className="flex items-center gap-1 py-1">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '');
                      const isBlock = !props.inline && match;
                      return isBlock ? (
                        <SyntaxHighlighter
                          style={oneDark as any}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ borderRadius: '0.75rem', fontSize: '0.8rem' }}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>{children}</code>
                      );
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>
          )}
        </div>

        {/* Bot message footer */}
        {!isUser && !message.isStreaming && message.content && (
          <div className="flex flex-col gap-2">
            {/* Confidence & latency */}
            <div className="flex items-center gap-3">
              {message.metadata?.confidence && (
                <span className={`status-badge status-${message.metadata.confidence}`}>
                  {message.metadata.confidence} confidence
                </span>
              )}
              {message.metadata?.total_latency_ms && (
                <span className="flex items-center gap-1 text-[10px] text-zinc-600">
                  <Clock size={9} />
                  {(message.metadata.total_latency_ms / 1000).toFixed(1)}s
                </span>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => onCopy(message.content)}
                className="btn-ghost p-1.5 rounded-lg text-[11px]"
                title="Copy"
              >
                <Copy size={12} />
              </button>
              <button
                onClick={() => onFeedback(message.id, 1)}
                className={`btn-ghost p-1.5 rounded-lg ${feedbackGiven === 1 ? 'text-green-400' : ''}`}
                title="Helpful"
                disabled={!!feedbackGiven}
              >
                <ThumbsUp size={12} />
              </button>
              <button
                onClick={() => onFeedback(message.id, -1)}
                className={`btn-ghost p-1.5 rounded-lg ${feedbackGiven === -1 ? 'text-red-400' : ''}`}
                title="Not helpful"
                disabled={!!feedbackGiven}
              >
                <ThumbsDown size={12} />
              </button>
              {citations.length > 0 && (
                <button
                  onClick={() => setCitationsOpen(!citationsOpen)}
                  className={`btn-ghost p-1.5 rounded-lg text-[11px] gap-1 ${citationsOpen ? 'text-violet-400' : ''}`}
                >
                  <FileText size={12} />
                  {citations.length} source{citations.length > 1 ? 's' : ''}
                </button>
              )}
            </div>

            {/* Citations panel */}
            {citationsOpen && citations.length > 0 && (
              <div className="flex flex-col gap-2 animate-fade-in">
                <p className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wide">Sources</p>
                {citations.map((c: Citation, i: number) => (
                  <div key={i} className="citation-card">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="text-xs font-semibold text-violet-300">
                        [{i + 1}] {c.document_title}
                      </span>
                      {c.page_number && (
                        <span className="text-[10px] text-zinc-600 flex-shrink-0">p.{c.page_number}</span>
                      )}
                    </div>
                    <p className="text-[11px] text-zinc-500 line-clamp-2 leading-relaxed">
                      {c.chunk_content}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {c.department && (
                        <span className="text-[10px] text-zinc-600 bg-zinc-800 rounded px-1.5 py-0.5">
                          {c.department}
                        </span>
                      )}
                      <span className="text-[10px] text-zinc-700">
                        {(c.similarity_score * 100).toFixed(0)}% match
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
