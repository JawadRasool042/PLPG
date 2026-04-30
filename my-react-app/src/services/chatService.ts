const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';
const USER_ACCESS_TOKEN_KEY = 'plpg_access_token';

// Helper for fetch with timeout
const fetchWithTimeout = async (url: string, options: RequestInit = {}, timeoutMs: number = 30000): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeoutMs}ms`);
    }
    throw error;
  }
};

export interface ChatContact {
  id: string;
  name: string;
  role: string;
  avatar: string;
  online_status: boolean;
  last_message: string;
  unread_count: number;
  last_message_at?: string | null;
}

export interface ChatMessage {
  id: string;
  sender_id: string;
  receiver_id: string;
  text: string;
  is_read: boolean;
  created_at: string;
  updated_at?: string | null;
}

const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export const getChatContacts = async (): Promise<ChatContact[]> => {
  const response = await fetchWithTimeout(`${API_BASE_URL}/chat/contacts`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.message || data?.detail || 'Failed to load contacts');
  }

  return data.contacts || [];
};

export const getConversationMessages = async (contactId: string): Promise<ChatMessage[]> => {
  const response = await fetchWithTimeout(`${API_BASE_URL}/chat/messages/${contactId}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.message || data?.detail || 'Failed to load messages');
  }

  return data.messages || [];
};

export const sendChatMessage = async (contactId: string, text: string): Promise<ChatMessage> => {
  const response = await fetchWithTimeout(`${API_BASE_URL}/chat/messages/${contactId}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ text }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.message || data?.detail || 'Failed to send message');
  }

  return data.message;
};
