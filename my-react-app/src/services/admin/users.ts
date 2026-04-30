import { adminApi } from './client';
import type { PaginatedResult, UserRow } from './types';

export const fetchUsers = async (params: {
  page?: number;
  limit?: number;
  search?: string;
  status?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}): Promise<PaginatedResult<UserRow>> => {
  try {
    console.log('Fetching users with params:', params);
    
    const { data } = await adminApi.get<{ 
      success: boolean;
      data: UserRow[];
      pagination: PaginatedResult<UserRow>['pagination'];
    }>('/users', {
      params,
    });

    console.log('Users API Response:', { success: data.success, count: data.data?.length, pagination: data.pagination });

    return {
      data: data.data || [],
      pagination: data.pagination || { page: 1, limit: 10, total: 0, pages: 0 },
    };
  } catch (error) {
    console.error('Error fetching users:', error);
    throw error;
  }
};

export const fetchUserDetails = async (id: string) => {
  const { data } = await adminApi.get(`/users/${id}`);
  return data.data;
};

export const changeUserRole = async (id: string, role: string) => {
  const { data } = await adminApi.patch(`/users/${id}/role`, { role });
  return data;
};

export const resetUserPassword = async (id: string) => {
  const { data } = await adminApi.post(`/users/${id}/reset-password`);
  return data;
};

export const suspendUser = async (id: string, reason?: string) => {
  const { data } = await adminApi.post(`/users/${id}/suspend`, { reason });
  return data;
};

export const activateUser = async (id: string) => {
  const { data } = await adminApi.post(`/users/${id}/activate`);
  return data;
};

export const deleteUser = async (id: string) => {
  const { data } = await adminApi.delete(`/users/${id}`);
  return data;
};

export const exportUsersCsv = async () => {
  const response = await adminApi.get('/users/export/csv', {
    responseType: 'blob',
  });
  return response.data;
};
