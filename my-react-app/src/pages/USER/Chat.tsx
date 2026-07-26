import React, { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../../config/apiBase';
import { CommunityChatBox } from '../../components/CommunityChatBox';
import { Users, MessageSquare } from 'lucide-react';

const API = API_BASE_URL;
const TOKEN_KEY = 'plpg_access_token';

const getToken = () => localStorage.getItem(TOKEN_KEY);

const apiFetch = async (path: string, opts: RequestInit = {}) => {
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
};

interface Contact {
  _id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  avatar?: string;
  lastMessage: string;
  lastMessageAt: string | null;
  unread: number;
}

interface Message {
  _id: string;
  senderId: string;
  receiverId: string;
  text: string;
  read: boolean;
  createdAt: string;
}

interface Community {
  _id: string;
  name: string;
  course: string;
  description: string;
  memberCount?: number;
}

const Chat: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'direct' | 'communities'>('direct');
  
  // Direct Messages State
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selected, setSelected] = useState<Contact | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  
  // Communities State
  const [communities, setCommunities] = useState<Community[]>([]);
  const [myCommunities, setMyCommunities] = useState<string[]>([]);
  const [selectedCommunity, setSelectedCommunity] = useState<Community | null>(null);
  const [transitioningId, setTransitioningId] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [myId, setMyId] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setMyId(payload.id || payload.sub || '');
    } catch {}
  }, []);

  const loadContacts = useCallback(async () => {
    try {
      const res = await apiFetch('/messages/contacts');
      setContacts(res.data || []);
    } catch (e) {
      console.error('Failed to load contacts', e);
    }
  }, []);

  const loadCommunities = useCallback(async () => {
    try {
      const [allRes, myRes] = await Promise.all([
        apiFetch('/community/'),
        apiFetch('/community/my')
      ]);
      setCommunities(allRes.data || []);
      setMyCommunities((myRes.data || []).map((c: Community) => c._id));
    } catch (e) {
      console.error('Failed to load communities', e);
    }
  }, []);

  useEffect(() => { 
    loadContacts(); 
    loadCommunities();
  }, [loadContacts, loadCommunities]);

  const loadConversation = useCallback(async (contactId: string) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/messages/conversation/${contactId}`);
      setMessages(res.data || []);
      loadContacts();
    } catch (e) {
      console.error('Failed to load conversation', e);
    } finally {
      setLoading(false);
    }
  }, [loadContacts]);

  useEffect(() => {
    if (activeTab !== 'direct' || !selected) return;
    loadConversation(selected._id);

    pollRef.current = setInterval(() => loadConversation(selected._id), 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [selected, activeTab, loadConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!text.trim() || !selected || sending) return;
    setSending(true);
    try {
      const res = await apiFetch('/messages/send', {
        method: 'POST',
        body: JSON.stringify({ receiverId: selected._id, text: text.trim() }),
      });
      setMessages(prev => [...prev, res.data]);
      setText('');
      loadContacts();
    } catch (e) {
      console.error('Send failed', e);
    } finally {
      setSending(false);
    }
  };

  const deleteMessage = async (msgId: string) => {
    try {
      await apiFetch(`/messages/${msgId}`, { method: 'DELETE' });
      setMessages(prev => prev.filter(m => m._id !== msgId));
    } catch {}
  };

  const toggleJoinCommunity = async (cId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (transitioningId) return;
    const isJoined = myCommunities.includes(cId);
    
    setTransitioningId(cId);
    
    try {
      await apiFetch(`/community/${cId}/${isJoined ? 'leave' : 'join'}`, { method: 'POST' });
      
      setTimeout(() => {
        if (isJoined && selectedCommunity?._id === cId) setSelectedCommunity(null);
        loadCommunities();
        setTransitioningId(null);
      }, 1000);
    } catch (err) {
      console.error(err);
      setTransitioningId(null);
    }
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    return isToday
      ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const initials = (c: Contact) =>
    `${c.firstName?.[0] || ''}${c.lastName?.[0] || ''}`.toUpperCase() || c.email[0].toUpperCase();

  const filteredContacts = contacts.filter(c =>
    `${c.firstName} ${c.lastName} ${c.email}`.toLowerCase().includes(search.toLowerCase())
  );
  const instructors = filteredContacts.filter(c => c.role === 'Teacher');
  const students = filteredContacts.filter(c => c.role !== 'Teacher');

  const filteredCommunities = communities.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) || 
    c.course.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pt-20 pb-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Inbox & Communities</h1>
            <p className="text-gray-600 mt-1">Connect with instructors and classmates</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden" style={{ height: 'calc(100vh - 220px)' }}>
          <div className="flex h-full">

            {/* Sidebar */}
            <div className="w-80 border-r border-gray-200 flex flex-col bg-white">
              
              {/* Tabs */}
              <div className="flex border-b border-gray-200">
                <button 
                  onClick={() => setActiveTab('direct')}
                  className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 ${activeTab === 'direct' ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50/50' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}`}
                >
                  <MessageSquare className="w-4 h-4" /> Direct
                </button>
                <button 
                  onClick={() => setActiveTab('communities')}
                  className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 ${activeTab === 'communities' ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50/50' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}`}
                >
                  <Users className="w-4 h-4" /> Communities
                </button>
              </div>

              {/* Search */}
              <div className="p-4 border-b border-gray-200">
                <input
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder={activeTab === 'direct' ? "Search contacts..." : "Search communities..."}
                  className="w-full pl-4 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-gray-50"
                />
              </div>

              {/* List */}
              <div className="flex-1 overflow-y-auto">
                {activeTab === 'direct' ? (
                  <>
                    {instructors.length > 0 && (
                      <div>
                        <div className="px-4 py-2 bg-indigo-50 border-b border-indigo-100">
                          <span className="text-xs font-bold text-indigo-700 uppercase tracking-wide">Teachers ({instructors.length})</span>
                        </div>
                        {instructors.map(c => <ContactItem key={c._id} contact={c} selected={selected?._id === c._id} onClick={() => setSelected(c)} initials={initials(c)} color="from-indigo-500 to-purple-600" />)}
                      </div>
                    )}
                    {students.length > 0 && (
                      <div>
                        <div className="px-4 py-2 bg-green-50 border-b border-green-100">
                          <span className="text-xs font-bold text-green-700 uppercase tracking-wide">Students ({students.length})</span>
                        </div>
                        {students.map(c => <ContactItem key={c._id} contact={c} selected={selected?._id === c._id} onClick={() => setSelected(c)} initials={initials(c)} color="from-green-500 to-emerald-600" />)}
                      </div>
                    )}
                    {filteredContacts.length === 0 && (
                      <div className="p-8 text-center text-gray-500 text-sm">No contacts found</div>
                    )}
                  </>
                ) : (
                  <>
                    {(() => {
                      const joined = filteredCommunities.filter(c => myCommunities.includes(c._id));
                      const other = filteredCommunities.filter(c => !myCommunities.includes(c._id));

                      return (
                        <div className="flex flex-col h-full overflow-y-auto">
                          <details open className="group border-b border-gray-200">
                            <summary className="flex items-center justify-between px-4 py-3 bg-indigo-50 cursor-pointer list-none hover:bg-indigo-100 transition-colors">
                              <span className="text-xs font-bold text-indigo-700 uppercase tracking-wide">My Communities ({joined.length})</span>
                              <svg className="w-4 h-4 text-indigo-500 transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </summary>
                            <div className="bg-white">
                              {joined.map(c => (
                                <div key={c._id} 
                                  onClick={() => setSelectedCommunity(c)}
                                  className={`w-full p-4 flex items-start gap-3 transition-colors border-b border-gray-100 cursor-pointer ${selectedCommunity?._id === c._id ? 'bg-indigo-50' : 'hover:bg-gray-50'}`}
                                >
                                  <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                                    <span className="text-lg font-bold text-white">#</span>
                                  </div>
                                  <div className="flex-1 text-left min-w-0">
                                    <p className="font-semibold text-gray-900 text-sm truncate">{c.name}</p>
                                    <p className="text-xs text-gray-500 truncate mt-0.5">{c.memberCount || 0} members</p>
                                  </div>
                                  <button 
                                    onClick={(e) => toggleJoinCommunity(c._id, e)}
                                    disabled={transitioningId === c._id}
                                    className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${transitioningId === c._id ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                                  >
                                    {transitioningId === c._id ? 'Left' : 'Leave'}
                                  </button>
                                </div>
                              ))}
                              {joined.length === 0 && (
                                <div className="p-6 text-center text-gray-500 text-sm border-b border-gray-100">You haven't joined any communities yet.</div>
                              )}
                            </div>
                          </details>

                          <details className="group border-b border-gray-200">
                            <summary className="flex items-center justify-between px-4 py-3 bg-gray-50 cursor-pointer list-none hover:bg-gray-100 transition-colors">
                              <span className="text-xs font-bold text-gray-600 uppercase tracking-wide">Discover Communities ({other.length})</span>
                              <svg className="w-4 h-4 text-gray-400 transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </summary>
                            <div className="bg-white">
                              {other.map(c => (
                                <div key={c._id} 
                                  className="w-full p-4 flex items-start gap-3 transition-colors border-b border-gray-100 opacity-75 cursor-default hover:bg-gray-50"
                                >
                                  <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center flex-shrink-0">
                                    <span className="text-lg font-bold text-white">#</span>
                                  </div>
                                  <div className="flex-1 text-left min-w-0">
                                    <p className="font-semibold text-gray-900 text-sm truncate">{c.name}</p>
                                    <p className="text-xs text-gray-500 truncate mt-0.5">{c.memberCount || 0} members</p>
                                  </div>
                                  <button 
                                    onClick={(e) => toggleJoinCommunity(c._id, e)}
                                    disabled={transitioningId === c._id}
                                    className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${transitioningId === c._id ? 'bg-emerald-500 text-white' : 'bg-indigo-600 text-white hover:bg-indigo-700'}`}
                                  >
                                    {transitioningId === c._id ? 'Joined' : 'Join'}
                                  </button>
                                </div>
                              ))}
                              {other.length === 0 && (
                                <div className="p-6 text-center text-gray-500 text-sm border-b border-gray-100">No more communities to discover.</div>
                              )}
                            </div>
                          </details>
                        </div>
                      );
                    })()}
                  </>
                )}
              </div>
            </div>

            {/* Chat Pane */}
            {activeTab === 'direct' ? (
              selected ? (
                <div className="flex-1 flex flex-col">
                  {/* Direct Message Chat Code */}
                  <div className="p-4 border-b border-gray-200 flex items-center gap-3 bg-white">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-semibold text-sm">
                      {initials(selected)}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{selected.firstName} {selected.lastName}</p>
                      <p className="text-xs text-gray-500">{selected.role} • {selected.email}</p>
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
                    {loading && <p className="text-center text-sm text-gray-400">Loading...</p>}
                    {!loading && messages.length === 0 && (
                      <div className="text-center text-gray-400 mt-10">
                        <p className="text-4xl mb-2">💬</p>
                        <p className="text-sm">No messages yet. Say hello!</p>
                      </div>
                    )}
                    {messages.map(msg => {
                      const isOwn = msg.senderId === myId;
                      return (
                        <div key={msg._id} className={`flex ${isOwn ? 'justify-end' : 'justify-start'} group`}>
                          <div className="max-w-xs lg:max-w-md">
                            <div className={`px-4 py-2 rounded-2xl text-sm ${isOwn ? 'bg-indigo-600 text-white rounded-br-sm' : 'bg-white text-gray-900 border border-gray-200 rounded-bl-sm'}`}>
                              {msg.text}
                            </div>
                            <div className={`flex items-center gap-2 mt-1 ${isOwn ? 'justify-end' : 'justify-start'}`}>
                              <span className="text-xs text-gray-400">{formatTime(msg.createdAt)}</span>
                              {isOwn && (
                                <button onClick={() => deleteMessage(msg._id)} className="text-xs text-red-400 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-600">
                                  delete
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    <div ref={bottomRef} />
                  </div>

                  <div className="p-4 border-t border-gray-200 bg-white">
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={text}
                        onChange={e => setText(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                        placeholder={`Message ${selected.firstName}...`}
                        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-gray-50"
                        maxLength={2000}
                      />
                      <button
                        onClick={sendMessage}
                        disabled={!text.trim() || sending}
                        className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                      >
                        {sending ? '...' : 'Send'}
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center bg-gray-50">
                  <div className="text-center">
                    <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4 text-4xl">💬</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">Select a conversation</h3>
                    <p className="text-sm text-gray-500">Choose a contact from the sidebar to start chatting</p>
                  </div>
                </div>
              )
            ) : (
              selectedCommunity ? (
                <CommunityChatBox community={selectedCommunity} myId={myId} />
              ) : (
                <div className="flex-1 flex items-center justify-center bg-gray-50">
                  <div className="text-center">
                    <div className="w-20 h-20 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4 text-4xl">👥</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">Join a Community</h3>
                    <p className="text-sm text-gray-500 max-w-sm mx-auto">Select a community from the sidebar that you have joined to view its real-time chat.</p>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const ContactItem: React.FC<{
  contact: Contact;
  selected: boolean;
  onClick: () => void;
  initials: string;
  color: string;
}> = ({ contact, selected, onClick, initials, color }) => (
  <button
    onClick={onClick}
    className={`w-full p-4 flex items-start gap-3 hover:bg-gray-50 transition-colors border-b border-gray-100 ${selected ? 'bg-indigo-50' : ''}`}
  >
    <div className={`w-11 h-11 rounded-full bg-gradient-to-br ${color} flex items-center justify-center flex-shrink-0`}>
      <span className="text-sm font-semibold text-white">{initials}</span>
    </div>
    <div className="flex-1 text-left min-w-0">
      <div className="flex items-center justify-between">
        <p className="font-semibold text-gray-900 text-sm truncate">{contact.firstName} {contact.lastName}</p>
        {contact.unread > 0 && (
          <span className="bg-indigo-600 text-white text-xs font-bold px-2 py-0.5 rounded-full ml-1">{contact.unread}</span>
        )}
      </div>
      <p className="text-xs text-gray-500 truncate mt-0.5">{contact.lastMessage || contact.email}</p>
    </div>
  </button>
);

export default Chat;
