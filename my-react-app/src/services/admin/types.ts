export interface AdminRole {
  _id: string;
  name: 'super_admin' | 'admin' | 'moderator' | 'viewer' | string;
  description?: string;
}

export interface Permission {
  _id: string;
  name: string;
  description?: string;
  category?: string;
  action?: string;
}

export interface AdminProfile {
  id: string;
  name: string;
  email: string;
  role: AdminRole;
  permissions: Permission[];
  status: 'active' | 'inactive' | 'suspended';
  lastLogin?: string;
  createdAt?: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  data: {
    accessToken: string;
    refreshToken: string;
    admin: AdminProfile;
  };
}

export interface PaginatedResult<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface UserRow {
  _id: string;
  name: string;
  firstName: string;
  lastName: string;
  email: string;
  emailVerified?: boolean;
  suspended?: boolean;
  status?: 'verified' | 'pending' | 'suspended';
  createdAt?: string;
}

export interface AuditLogRow {
  _id: string;
  action: string;
  resource: string;
  description: string;
  status: string;
  ipAddress?: string;
  createdAt: string;
  admin?: {
    name: string;
    email: string;
  };
}

export interface DashboardMetrics {
  metrics: {
    users: {
      total: number;
      verified: number;
      newThisWeek: number;
      newThisMonth: number;
    };
    activity: {
      totalLogins: number;
      failedLogins: number;
      adminActionsThisWeek: number;
    };
  };
  charts: {
    userGrowth: { _id: string; count: number }[];
  };
  recentActivities: AuditLogRow[];
}

