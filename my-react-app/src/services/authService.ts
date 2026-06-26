import { API_BASE_URL } from '../config/apiBase';

const USER_ACCESS_TOKEN_KEY = 'plpg_access_token';
const USER_REFRESH_TOKEN_KEY = 'plpg_refresh_token';

export interface UserData {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
  isActive: boolean;
  createdAt: Date;
}

/** Return type for successful registration (same shape as logged-in user payload). */
export type RegisterResult = UserData;

// Helper to get token expiry from JWT (without verification)
const getTokenExpiry = (token: string): number | null => {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const decoded = JSON.parse(atob(parts[1]));
    return decoded.exp ? decoded.exp * 1000 : null; // Convert to milliseconds
  } catch {
    return null;
  }
};

// Helper to check if token is expired
const isTokenExpired = (token: string): boolean => {
  const expiry = getTokenExpiry(token);
  if (!expiry) return true;
  return Date.now() >= expiry - 60000; // Refresh 1 minute before expiry
};

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

// Refresh access token
export const refreshAccessToken = async (): Promise<boolean> => {
  const refreshToken = localStorage.getItem(USER_REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;

  try {
    const response = await fetchWithTimeout(`${API_BASE_URL}/auth/refresh-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      localStorage.removeItem(USER_ACCESS_TOKEN_KEY);
      localStorage.removeItem(USER_REFRESH_TOKEN_KEY);
      return false;
    }

    const data = await response.json();
    localStorage.setItem(USER_ACCESS_TOKEN_KEY, data.access_token);
    if (data.refresh_token) {
      localStorage.setItem(USER_REFRESH_TOKEN_KEY, data.refresh_token);
    }
    return true;
  } catch (error) {
    console.error('Token refresh failed:', error);
    localStorage.removeItem(USER_ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_REFRESH_TOKEN_KEY);
    return false;
  }
};

/** Return a valid access token, refreshing when near expiry. */
export const getValidAccessToken = async (): Promise<string | null> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) return null;

  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) return null;
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  }

  return token;
};

/** JSON auth headers with a valid (refreshed) access token when available. */
export const getAuthenticatedHeaders = async (): Promise<Record<string, string>> => {
  const token = await getValidAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

/**
 * fetch() wrapper that attaches a valid token and retries once after refresh on 401.
 */
export const authenticatedFetch = async (
  url: string,
  options: RequestInit = {},
): Promise<Response> => {
  const headers = await getAuthenticatedHeaders();
  const mergedHeaders = { ...headers, ...(options.headers as Record<string, string> | undefined) };

  let response = await fetch(url, { ...options, headers: mergedHeaders });

  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      const retryHeaders = await getAuthenticatedHeaders();
      response = await fetch(url, {
        ...options,
        headers: { ...retryHeaders, ...(options.headers as Record<string, string> | undefined) },
      });
    }
  }

  return response;
};

// Register a new user
export const registerUser = async (
  email: string,
  password: string,
  firstName: string,
  lastName: string,
  role: string = 'Student'
): Promise<UserData> => {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
      first_name: firstName,
      last_name: lastName,
      role,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }

  const user = await response.json();
  return {
    id: user.id.toString(),
    email: user.email,
    firstName: user.first_name,
    lastName: user.last_name,
    role: user.role,
    isActive: user.is_active,
    createdAt: new Date(user.created_at),
  };
};

// Login user
export const loginUser = async (email: string, password: string): Promise<UserData> => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  const tokenData = await response.json();
  localStorage.setItem(USER_ACCESS_TOKEN_KEY, tokenData.access_token);
  if (tokenData.refresh_token) {
    localStorage.setItem(USER_REFRESH_TOKEN_KEY, tokenData.refresh_token);
  }

  // Get user data
  const userResponse = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      'Authorization': `Bearer ${tokenData.access_token}`,
    },
  });

  if (!userResponse.ok) {
    throw new Error('Failed to get user data');
  }

  const user = await userResponse.json();
  return {
    id: user.id.toString(),
    email: user.email,
    firstName: user.first_name,
    lastName: user.last_name,
    role: user.role,
    isActive: user.is_active,
    createdAt: new Date(user.created_at),
  };
};

// Logout user
export const logoutUser = async (): Promise<void> => {
  localStorage.removeItem(USER_ACCESS_TOKEN_KEY);
  localStorage.removeItem(USER_REFRESH_TOKEN_KEY);
};

// Get current user data
export const getCurrentUserData = async (): Promise<UserData | null> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) return null;

  // Check if token is expired and refresh if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) return null;
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem(USER_ACCESS_TOKEN_KEY);
        localStorage.removeItem(USER_REFRESH_TOKEN_KEY);
      }
      return null;
    }

    const user = await response.json();
    return {
      id: user.id.toString(),
      email: user.email,
      firstName: user.first_name,
      lastName: user.last_name,
      role: user.role,
      isActive: user.is_active,
      createdAt: new Date(user.created_at),
    };
  } catch (error) {
    localStorage.removeItem(USER_ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_REFRESH_TOKEN_KEY);
    return null;
  }
};

// Listen to auth state changes (mock implementation for now)
export const onAuthStateChange = (callback: (user: UserData | null) => void) => {
  // In a real implementation, you might use WebSockets or polling
  const checkAuth = async () => {
    const user = await getCurrentUserData();
    callback(user);
  };
  checkAuth();
  return () => {}; // Mock unsubscribe
};

// Verify email with token
export const verifyEmail = async (token: string): Promise<{ success: boolean; message: string }> => {
  const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Email verification failed');
  }

  return {
    success: true,
    message: data.message || 'Email verified successfully!',
  };
};

// Resend verification email
export const resendVerificationEmail = async (email: string): Promise<{ success: boolean; message: string }> => {
  const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to resend verification email');
  }

  return {
    success: true,
    message: data.message || 'Verification email sent!',
  };
};

// Request password reset
export const forgotPassword = async (email: string): Promise<{ success: boolean; message: string }> => {
  const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to send password reset email');
  }

  return {
    success: true,
    message: data.message || 'Password reset email sent!',
  };
};

// Reset password with token
export const resetPassword = async (token: string, password: string): Promise<{ success: boolean; message: string }> => {
  const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Password reset failed');
  }

  return {
    success: true,
    message: data.message || 'Password reset successfully!',
  };
};

// Profile and Settings interfaces
export interface ProfileData {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  bio: string | null;
  avatar: string | null;
  date_of_birth: string | null;
  location: string | null;
  role: string;
  is_email_verified: boolean;
  created_at: string;
}

export interface SettingsData {
  preferences: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    timezone: string;
  };
  notifications: {
    email: boolean;
    quizReminders: boolean;
    progressUpdates: boolean;
    newsletter: boolean;
  };
  privacy: {
    profileVisibility: 'public' | 'private' | 'friends';
    showEmail: boolean;
  };
}

// Get user profile
export const getUserProfile = async (): Promise<ProfileData> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) throw new Error('Not authenticated');

  // Refresh token if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) throw new Error('Token refresh failed');
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_BASE_URL}/profile`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch profile');
  }

  return await response.json();
};

// Update user profile
export const updateUserProfile = async (profileData: Partial<ProfileData>): Promise<ProfileData> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) throw new Error('Not authenticated');

  // Refresh token if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) throw new Error('Token refresh failed');
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_BASE_URL}/profile`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(profileData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update profile');
  }

  const data = await response.json();
  return data.user;
};

// Update profile avatar
export const updateAvatar = async (avatarUrl: string): Promise<string> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) throw new Error('Not authenticated');

  // Refresh token if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) throw new Error('Token refresh failed');
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_BASE_URL}/profile/avatar`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ avatar: avatarUrl }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update avatar');
  }

  const data = await response.json();
  return data.avatar;
};

// Get user settings
export const getUserSettings = async (): Promise<SettingsData> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) throw new Error('Not authenticated');

  // Refresh token if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) throw new Error('Token refresh failed');
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_BASE_URL}/settings`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch settings');
  }

  const data = await response.json();
  return {
    preferences: data.preferences,
    notifications: data.notifications,
    privacy: data.privacy
  };
};

// Update user settings
export const updateUserSettings = async (settings: Partial<SettingsData>): Promise<SettingsData> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) throw new Error('Not authenticated');

  // Refresh token if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) throw new Error('Token refresh failed');
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_BASE_URL}/settings`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update settings');
  }

  const data = await response.json();
  return {
    preferences: data.preferences,
    notifications: data.notifications,
    privacy: data.privacy
  };
};

// Change password
export const changePassword = async (currentPassword: string, newPassword: string): Promise<{ message: string }> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) throw new Error('Not authenticated');

  // Refresh token if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) throw new Error('Token refresh failed');
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_BASE_URL}/settings/password`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: newPassword
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to change password');
  }

  return await response.json();
};

// Delete account
export const deleteAccount = async (password: string): Promise<{ message: string }> => {
  let token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
  if (!token) throw new Error('Not authenticated');

  // Refresh token if needed
  if (isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) throw new Error('Token refresh failed');
    token = localStorage.getItem(USER_ACCESS_TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
  }

  const response = await fetch(`${API_BASE_URL}/account`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      password,
      confirmation: 'DELETE'
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete account');
  }

  return await response.json();
};
