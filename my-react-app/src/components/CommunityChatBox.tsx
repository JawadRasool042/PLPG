import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { API_BASE_URL } from '../config/apiBase';
import { Paperclip, Reply, Search, X, ChevronUp, AtSign } from 'lucide-react';

const SOCKET_URL = API_BASE_URL === '/api' ? 'http://localhost:5000' : API_BASE_URL.replace('/api', '');

const EMOJI_LIST = ['👍', '❤️', '😂', '🎉', '🤔', '👀', '🔥', '💯'];

interface CommunityChatBoxProps {
  community: { _id: string; name: string; course: string; description: string };
  myId: string;
}

interface Sender {
  _id: string;
  firstName: string;
  lastName: string;
  avatar?: string;
}

interface Member {
  _id: string;
  firstName: string;
  lastName: string;
  email: string;
  avatar?: string;
}

interface Message {
  _id: string;
  sender_id: string;
  sender?: Sender;
  text: string;
  fileUrl?: string;
  parentMessageId?: string;
  mentions: string[];
  reactions: Record<string, string[]>;
  readBy?: string[];
  createdAt: string;
}

export const CommunityChatBox: React.FC<CommunityChatBoxProps> = ({ community, myId }) => {
  const socketRef = useRef<Socket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  const [onlineCount, setOnlineCount] = useState(0);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  // File preview state — set when user picks a file, cleared after send/cancel
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingFilePreview, setPendingFilePreview] = useState<string | null>(null); // object URL for images
  const [hasMore, setHasMore] = useState(false);
  const [totalMessages, setTotalMessages] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [toast, setToast] = useState<{message: string, type: 'error'|'success'|'info'} | null>(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // @mention state
  const [members, setMembers] = useState<Member[]>([]);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState('');
  const [selectedMentions, setSelectedMentions] = useState<string[]>([]);

  // Emoji picker state
  const [emojiPickerMsgId, setEmojiPickerMsgId] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const token = localStorage.getItem('plpg_access_token') || sessionStorage.getItem('plpg_access_token');

  // ── Fetch messages with pagination ──
  const fetchMessages = useCallback(async (searchQuery: string, skip = 0, append = false) => {
    try {
      const res = await fetch(
        `${API_BASE_URL}/community/${community._id}/messages?search=${encodeURIComponent(searchQuery)}&skip=${skip}&limit=50`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const json = await res.json();
      if (json.success) {
        if (append) {
          setMessages(prev => [...json.data, ...prev]);
        } else {
          setMessages(json.data);
        }
        setHasMore(json.hasMore || false);
        setTotalMessages(json.total || 0);
      }
    } catch (e) {
      console.error('Failed to fetch messages', e);
    }
  }, [community._id, token]);

  // ── Fetch members for @mention ──
  const fetchMembers = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/community/${community._id}/members`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const json = await res.json();
      if (json.success) setMembers(json.data || []);
    } catch (e) {
      console.error('Failed to fetch members', e);
    }
  }, [community._id, token]);

  useEffect(() => {
    // Reset state when switching communities
    setMessages([]);
    setSearch('');
    setReplyTo(null);
    setHasMore(false);
    setTotalMessages(0);
    setTypingUsers(new Set());
    setUploadProgress(null);
    setPendingFile(null);
    setPendingFilePreview(null);
    fetchMessages('');
    fetchMembers();
  }, [fetchMessages, fetchMembers]);

  // ── Load more (pagination) ──
  const loadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    const scrollEl = chatContainerRef.current;
    const prevScrollHeight = scrollEl?.scrollHeight || 0;

    await fetchMessages(search, messages.length, true);

    // Maintain scroll position after prepending older messages
    requestAnimationFrame(() => {
      if (scrollEl) {
        scrollEl.scrollTop = scrollEl.scrollHeight - prevScrollHeight;
      }
    });
    setLoadingMore(false);
  };

  // ── Socket connection ──
  useEffect(() => {
    const s = io(SOCKET_URL, { query: { token }, transports: ['websocket', 'polling'] });
    socketRef.current = s;

    s.on('connect', () => {
      s.emit('join_community', { community_id: community._id, token });
      setToast({ message: 'Connected to chat', type: 'success' });
    });

    s.on('disconnect', (reason) => {
      setToast({ message: `Disconnected from chat (${reason})`, type: 'error' });
    });

    s.on('new_message', (msg: Message) => {
      setMessages(prev => {
        // Prevent duplicate messages if we already appended it optimistically
        const isOptimistic = prev.some(m => m._id.startsWith('temp-') && m.text === msg.text && m.sender_id === msg.sender_id);
        if (isOptimistic) {
          return prev.map(m => (m._id.startsWith('temp-') && m.text === msg.text) ? msg : m);
        }
        if (prev.some(m => m._id === msg._id)) return prev;
        return [...prev, msg];
      });
    });

    s.on('user_status', (data: { user_id: string; status: string; online_count: number }) => {
      setOnlineCount(data.online_count);
    });

    s.on('user_typing', (data: { user_id: string; name: string; is_typing: boolean }) => {
      setTypingUsers(prev => {
        const next = new Set(prev);
        if (data.is_typing) next.add(data.name);
        else next.delete(data.name);
        return next;
      });
    });

    s.on('message_reaction_update', (data: { message_id: string; reactions: Record<string, string[]> }) => {
      setMessages(prev =>
        prev.map(m => (m._id === data.message_id ? { ...m, reactions: data.reactions } : m))
      );
    });

    s.on('read_receipt', (_data: { user_id: string; community_id: string }) => {
      // Could update read indicators here if needed
    });

    s.on('connect_error', (err: Error) => {
      console.error('Socket connection error:', err.message);
      setToast({ message: 'Connection error. Retrying...', type: 'error' });
    });

    return () => {
      s.emit('leave_community', { community_id: community._id, token });
      s.disconnect();
      socketRef.current = null;
    };
  }, [community._id, token]);

  // ── Auto-scroll on new messages ──
  const scrollToBottom = (smooth = true) => {
    const el = chatContainerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'instant' });
  };

  useEffect(() => {
    const timer = setTimeout(() => scrollToBottom(true), 50);
    return () => clearTimeout(timer);
  }, [messages]);

  // ── Mark read on focus ──
  useEffect(() => {
    const socket = socketRef.current;
    if (socket && community._id) {
      socket.emit('mark_read', { community_id: community._id, token });
    }
  }, [messages, community._id, token]);

  // ── Typing indicator (with proper useRef cleanup) ──
  const handleTyping = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setText(value);

    // @mention detection
    const lastAt = value.lastIndexOf('@');
    if (lastAt !== -1 && (lastAt === 0 || value[lastAt - 1] === ' ')) {
      const afterAt = value.substring(lastAt + 1);
      if (!afterAt.includes(' ')) {
        setShowMentions(true);
        setMentionFilter(afterAt.toLowerCase());
      } else {
        setShowMentions(false);
      }
    } else {
      setShowMentions(false);
    }

    import('../services/authService').then(({ getValidAccessToken }) => {
      getValidAccessToken().then(freshToken => {
        socketRef.current?.emit('typing', { community_id: community._id, is_typing: true, token: freshToken });
      }).catch(console.error);
    });

    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      import('../services/authService').then(({ getValidAccessToken }) => {
        getValidAccessToken().then(freshToken => {
          socketRef.current?.emit('typing', { community_id: community._id, is_typing: false, token: freshToken });
        }).catch(console.error);
      });
    }, 2000);
  };

  // ── Insert @mention ──
  const insertMention = (member: Member) => {
    const lastAt = text.lastIndexOf('@');
    const before = text.substring(0, lastAt);
    const name = `${member.firstName} ${member.lastName}`.trim();
    setText(`${before}@${name} `);
    setShowMentions(false);
    setSelectedMentions(prev => [...prev, member._id]);
  };

  // ── Send message (text OR pending file) ──
  const sendMessage = async () => {
    const hasText = !!text.trim();
    const hasFile = !!pendingFile;
    if ((!hasText && !hasFile) || uploading) return;

    // Save text state in case we need to rollback
    const messageText = text.trim();
    
    // Optimistically clear text so UI feels instant
    setText('');
    setReplyTo(null);
    setSelectedMentions([]);
    setShowMentions(false);

    if (hasFile && pendingFile) {
      setUploading(true);
      setUploadProgress(`Sending ${pendingFile.name}...`);
      try {
        const formData = new FormData();
        formData.append('file', pendingFile);

        const { getValidAccessToken } = await import('../services/authService');
        const tokenForUpload = await getValidAccessToken();
        
        // Use AbortController to prevent infinite hang on Render/Vercel
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout
        
        const res = await fetch(`${API_BASE_URL}/community/upload`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${tokenForUpload}` },
          body: formData,
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        const json = await res.json();
        if (json.success) {
          socketRef.current?.emit('send_message', {
            community_id: community._id,
            text: messageText || pendingFile.name,
            fileUrl: json.fileUrl,
            parentMessageId: replyTo?._id || null,
            mentions: selectedMentions,
            token: tokenForUpload,
          });
        } else {
          setText(messageText); // Restore on failure
          setToast({ message: json.message || 'Upload failed', type: 'error' });
        }
      } catch (err) {
        console.error(err);
        setText(messageText); // Restore on failure
        setToast({ message: 'Upload failed. Please try again.', type: 'error' });
      } finally {
        setUploading(false);
        setUploadProgress(null);
        setPendingFile(null);
        if (pendingFilePreview) URL.revokeObjectURL(pendingFilePreview);
        setPendingFilePreview(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    } else {
      // Text-only message: Optimistic UI
      const tempId = `temp-${Date.now()}`;
      const tempMsg: Message = {
        _id: tempId,
        sender_id: myId,
        text: messageText,
        mentions: selectedMentions,
        reactions: {},
        createdAt: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, tempMsg]);
      scrollToBottom();

      try {
        const { getValidAccessToken } = await import('../services/authService');
        const freshToken = await getValidAccessToken();
        socketRef.current?.emit('send_message', {
          community_id: community._id,
          text: messageText,
          parentMessageId: replyTo?._id || null,
          mentions: selectedMentions,
          token: freshToken,
        });
      } catch (err) {
        console.error('Failed to get token for message', err);
        setMessages(prev => prev.filter(m => m._id !== tempId));
        setText(messageText); // Restore on failure
        setToast({ message: 'Failed to send message. Please log in again.', type: 'error' });
      }
    }

    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    
    import('../services/authService').then(({ getValidAccessToken }) => {
      getValidAccessToken().then(freshToken => {
        socketRef.current?.emit('typing', { community_id: community._id, is_typing: false, token: freshToken });
      }).catch(console.error);
    });
  };

  // ── Cancel pending file ──
  const cancelPendingFile = () => {
    if (pendingFilePreview) URL.revokeObjectURL(pendingFilePreview);
    setPendingFile(null);
    setPendingFilePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // ── File selection — preview only, don't upload yet ──
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      setToast({ message: 'File is too large. Maximum size is 10MB.', type: 'error' });
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    // Revoke previous preview URL
    if (pendingFilePreview) URL.revokeObjectURL(pendingFilePreview);

    // Create preview URL for images
    const isImage = file.type.startsWith('image/');
    const previewUrl = isImage ? URL.createObjectURL(file) : null;

    setPendingFile(file);
    setPendingFilePreview(previewUrl);
  };

  // ── Toggle reaction ──
  const toggleReaction = (messageId: string, emoji: string) => {
    socketRef.current?.emit('message_react', {
      community_id: community._id,
      message_id: messageId,
      emoji,
      token,
    });
    setEmojiPickerMsgId(null);
  };

  // ── Filtered members for @mention dropdown ──
  const filteredMembers = members.filter(
    m =>
      m._id !== myId &&
      (`${m.firstName} ${m.lastName}`.toLowerCase().includes(mentionFilter) ||
        m.email.toLowerCase().includes(mentionFilter))
  );

  // ── Render mentions in text ──
  const renderText = (msgText: string) => {
    const parts = msgText.split(/(@\w[\w\s]*)/g);
    return parts.map((part, i) =>
      part.startsWith('@') ? (
        <span key={i} className="text-blue-300 font-semibold bg-blue-500/20 rounded px-0.5">
          {part}
        </span>
      ) : (
        <span key={i}>{part}</span>
      )
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-gray-50 relative">
      {/* Toast Notification */}
      {toast && (
        <div className={`absolute top-16 left-1/2 transform -translate-x-1/2 z-50 px-4 py-2 rounded-full shadow-lg font-medium text-xs text-white transition-all duration-300 animate-in fade-in slide-in-from-top-2 ${toast.type === 'error' ? 'bg-red-500' : toast.type === 'success' ? 'bg-emerald-500' : 'bg-blue-500'}`}>
          {toast.message}
        </div>
      )}
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-white flex justify-between items-center shadow-sm">
        <div>
          <h2 className="font-bold text-gray-900 text-lg"># {community.name}</h2>
          <p className="text-xs text-green-600 font-medium">
            ● {onlineCount} online · {totalMessages} messages
          </p>
        </div>
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search messages..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') fetchMessages(search);
              if (e.key === 'Escape') {
                setSearch('');
                fetchMessages('');
              }
            }}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-full text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Chat Area */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Load More */}
        {hasMore && (
          <div className="text-center">
            <button
              onClick={loadMore}
              disabled={loadingMore}
              className="inline-flex items-center gap-1 px-4 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-full hover:bg-indigo-100 transition-colors disabled:opacity-50"
            >
              <ChevronUp className="w-3 h-3" />
              {loadingMore ? 'Loading...' : 'Load earlier messages'}
            </button>
          </div>
        )}

        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-10">
            <p className="text-4xl mb-2">💬</p>
            <p className="text-sm">No messages yet. Start the conversation!</p>
          </div>
        )}

        {messages.map(msg => {
          const isOwn = msg.sender_id === myId;
          const senderName = msg.sender
            ? `${msg.sender.firstName} ${msg.sender.lastName}`
            : 'Unknown';
          const parentMsg = msg.parentMessageId
            ? messages.find(m => m._id === msg.parentMessageId)
            : null;

          return (
            <div key={msg._id} className={`flex ${isOwn ? 'justify-end' : 'justify-start'} group`}>
              <div className="max-w-xl">
                {!isOwn && (
                  <p className="text-xs text-gray-500 mb-1 ml-1 font-medium">{senderName}</p>
                )}

                {parentMsg && (
                  <div
                    className={`text-xs p-2 mb-1 rounded-md opacity-75 ${
                      isOwn
                        ? 'bg-indigo-700/50 text-indigo-100'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    <Reply className="inline w-3 h-3 mr-1" />
                    Replying to: {parentMsg.text.substring(0, 50)}
                    {parentMsg.text.length > 50 ? '...' : ''}
                  </div>
                )}

                <div
                  className={`px-4 py-2.5 text-sm relative ${
                    isOwn
                      ? 'bg-indigo-600 text-white rounded-2xl rounded-br-sm'
                      : 'bg-white text-gray-900 border border-gray-200 rounded-2xl rounded-bl-sm shadow-sm'
                  }`}
                >
                  {msg.text && !msg.fileUrl && <p className="leading-relaxed">{renderText(msg.text)}</p>}
                  {msg.fileUrl && (
                    <div>
                      {msg.fileUrl.match(/\.(jpeg|jpg|gif|png|webp)$/i) ? (
                        <div>
                          {msg.text && (
                            <p className="text-xs opacity-70 mb-1">{msg.text}</p>
                          )}
                          <img
                            src={`${SOCKET_URL}${msg.fileUrl}`}
                            alt={msg.text || 'attachment'}
                            className="max-w-[240px] rounded-lg border border-white/20 cursor-pointer"
                            onClick={() => window.open(`${SOCKET_URL}${msg.fileUrl}`, '_blank')}
                          />
                        </div>
                      ) : (
                        <a
                          href={`${SOCKET_URL}${msg.fileUrl}`}
                          target="_blank"
                          rel="noreferrer"
                          className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                            isOwn
                              ? 'bg-indigo-700 text-white hover:bg-indigo-800'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          <Paperclip className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate max-w-[180px]">{msg.text || 'Download File'}</span>
                        </a>
                      )}
                    </div>
                  )}

                  {/* Timestamp */}
                  <p
                    className={`text-[10px] mt-1 ${
                      isOwn ? 'text-indigo-200' : 'text-gray-400'
                    }`}
                  >
                    {new Date(msg.createdAt).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>

                  {/* Action buttons (hover) */}
                  <div
                    className={`absolute top-1/2 -translate-y-1/2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ${
                      isOwn ? '-left-20' : '-right-20'
                    }`}
                  >
                    <button
                      onClick={() =>
                        setEmojiPickerMsgId(prev => (prev === msg._id ? null : msg._id))
                      }
                      className="p-1.5 bg-white shadow-sm rounded-full text-gray-500 hover:bg-gray-50 border border-gray-200 text-xs"
                      title="React"
                    >
                      😊
                    </button>
                    <button
                      onClick={() => setReplyTo(msg)}
                      className="p-1.5 bg-white shadow-sm rounded-full text-gray-500 hover:bg-gray-50 border border-gray-200"
                      title="Reply"
                    >
                      <Reply className="w-3 h-3" />
                    </button>
                  </div>

                  {/* Emoji picker dropdown */}
                  {emojiPickerMsgId === msg._id && (
                    <div
                      className={`absolute z-10 bg-white border border-gray-200 rounded-xl shadow-lg p-2 flex gap-1 ${
                        isOwn ? '-left-44 top-0' : '-right-44 top-0'
                      }`}
                    >
                      {EMOJI_LIST.map(emoji => (
                        <button
                          key={emoji}
                          onClick={() => toggleReaction(msg._id, emoji)}
                          className="text-lg hover:scale-125 transition-transform p-1"
                        >
                          {emoji}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Reactions */}
                {Object.keys(msg.reactions || {}).length > 0 && (
                  <div className={`flex gap-1 mt-1 flex-wrap ${isOwn ? 'justify-end' : 'justify-start'}`}>
                    {Object.entries(msg.reactions).map(([emoji, users]) => (
                      <button
                        key={emoji}
                        onClick={() => toggleReaction(msg._id, emoji)}
                        className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                          users.includes(myId)
                            ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                            : 'bg-white border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        {emoji} {users.length}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Typing Indicator */}
      {typingUsers.size > 0 && (
        <div className="px-4 py-1.5 text-xs text-gray-400 italic bg-gray-50/80 border-t border-gray-100">
          <span className="inline-flex items-center gap-1">
            <span className="flex gap-0.5">
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
            {Array.from(typingUsers).join(', ')} {typingUsers.size === 1 ? 'is' : 'are'} typing
          </span>
        </div>
      )}

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-gray-200 relative">
        {/* @Mention dropdown */}
        {showMentions && filteredMembers.length > 0 && (
          <div className="absolute bottom-full left-4 right-4 mb-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-40 overflow-y-auto z-20">
            {filteredMembers.slice(0, 8).map(m => (
              <button
                key={m._id}
                onClick={() => insertMention(m)}
                className="w-full px-4 py-2 flex items-center gap-2 hover:bg-indigo-50 text-left text-sm"
              >
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-semibold">
                  {m.firstName?.[0] || '?'}
                </div>
                <div>
                  <span className="font-medium text-gray-900">
                    {m.firstName} {m.lastName}
                  </span>
                  <span className="text-gray-400 ml-2 text-xs">{m.email}</span>
                </div>
              </button>
            ))}
          </div>
        )}

        {replyTo && (
          <div className="flex items-center justify-between bg-gray-50 p-2 rounded-t-xl border-l-4 border-indigo-500 mb-2">
            <span className="text-xs text-gray-600 truncate">
              <Reply className="inline w-3 h-3 mr-1" /> Replying to: {replyTo.text}
            </span>
            <button
              onClick={() => setReplyTo(null)}
              className="text-gray-400 hover:text-gray-600 ml-2"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept="image/*,.pdf,.doc,.docx,.txt,.zip,.mp4,.mp3"
            onChange={handleFileSelect}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className={`p-2 transition-colors rounded-full flex-shrink-0 ${
              uploading
                ? 'text-indigo-500 bg-indigo-50 animate-pulse cursor-not-allowed'
                : pendingFile
                ? 'text-indigo-600 bg-indigo-50'
                : 'text-gray-400 hover:text-indigo-600 bg-gray-50'
            }`}
            disabled={uploading}
            title="Attach file (images, PDF, Word, etc.)"
          >
            <Paperclip className="w-5 h-5" />
          </button>
          <button
            onClick={() => {
              setText(prev => prev + '@');
              setShowMentions(true);
              setMentionFilter('');
            }}
            className="p-2 text-gray-400 hover:text-indigo-600 transition-colors bg-gray-50 rounded-full flex-shrink-0"
            title="Mention someone"
          >
            <AtSign className="w-5 h-5" />
          </button>

          {/* File preview chip — shown above text input when file is pending */}
          {pendingFile ? (
            <div className="flex-1 flex flex-col gap-1.5">
              <div className="flex items-center gap-2 px-3 py-1.5 border border-indigo-300 rounded-xl bg-indigo-50">
                {pendingFilePreview ? (
                  <img src={pendingFilePreview} alt="preview" className="w-8 h-8 rounded object-cover flex-shrink-0 border border-indigo-200" />
                ) : (
                  <div className="w-8 h-8 rounded bg-indigo-100 border border-indigo-200 flex items-center justify-center flex-shrink-0">
                    <Paperclip className="w-3.5 h-3.5 text-indigo-500" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-indigo-800 truncate">{pendingFile.name}</p>
                  <p className="text-[10px] text-indigo-500">{(pendingFile.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  onClick={cancelPendingFile}
                  className="p-1 text-indigo-400 hover:text-red-500 transition-colors flex-shrink-0"
                  title="Remove file"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <input
                type="text"
                value={text}
                onChange={handleTyping}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey && !showMentions) sendMessage();
                  if (e.key === 'Escape') setShowMentions(false);
                }}
                placeholder={uploading ? uploadProgress || 'Uploading...' : 'Add a caption (optional)...'}
                disabled={uploading}
                autoFocus
                className="px-4 py-2 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-gray-50 disabled:bg-gray-100 w-full"
              />
            </div>
          ) : (
            <input
              type="text"
              value={text}
              onChange={handleTyping}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey && !showMentions) sendMessage();
                if (e.key === 'Escape') setShowMentions(false);
              }}
              placeholder={uploading ? uploadProgress || 'Uploading...' : 'Type a message... (@ to mention)'}
              disabled={uploading}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400"
            />
          )}

          <button
            onClick={sendMessage}
            disabled={(!text.trim() && !pendingFile) || uploading}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm font-medium shadow-sm flex-shrink-0"
          >
            {uploading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};
