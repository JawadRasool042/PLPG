import axios from 'axios';

import { API_BASE_URL } from '../../config/apiBase';

export const ADMIN_ACCESS_TOKEN_KEY = 'plpg_admin_access_token';
export const ADMIN_REFRESH_TOKEN_KEY = 'plpg_admin_refresh_token';

export const adminApi = axios.create({
  baseURL: `${API_BASE_URL}/admin`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add token
adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem(ADMIN_ACCESS_TOKEN_KEY);
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle token refresh
adminApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retried, try to refresh token
    if (error?.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem(ADMIN_REFRESH_TOKEN_KEY);
        if (!refreshToken) {
          clearAdminTokens();
          return Promise.reject(error);
        }

        // Call refresh endpoint
        const response = await axios.post(`${API_BASE_URL}/admin/auth/refresh-token`, {
          refreshToken,
        });

        const { accessToken, refreshToken: newRefreshToken } = response.data.data;
        setAdminTokens(accessToken, newRefreshToken);

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return adminApi(originalRequest);
      } catch (refreshError) {
        clearAdminTokens();
        return Promise.reject(refreshError);
      }
    }

    if (error?.response?.status === 401) {
      clearAdminTokens();
    }

    return Promise.reject(error);
  }
);

export const setAdminTokens = (access: string, refresh?: string) => {
  localStorage.setItem(ADMIN_ACCESS_TOKEN_KEY, access);
  if (refresh) {
    localStorage.setItem(ADMIN_REFRESH_TOKEN_KEY, refresh);
  }
};

export const clearAdminTokens = () => {
  localStorage.removeItem(ADMIN_ACCESS_TOKEN_KEY);
  localStorage.removeItem(ADMIN_REFRESH_TOKEN_KEY);
};

export const getAdminAccessToken = () => localStorage.getItem(ADMIN_ACCESS_TOKEN_KEY);

