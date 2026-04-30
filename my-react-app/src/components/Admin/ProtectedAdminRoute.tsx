import React, { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAdminStore } from '../../store/useAdminStore';
import { getAdminAccessToken } from '../../services/admin/client';

const ProtectedAdminRoute: React.FC = () => {
  const { isAuthenticated, admin, fetchProfile, loading } = useAdminStore();
  const location = useLocation();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    // Allow hardcoded local admin without token
    if (isAuthenticated && admin?.email === 'admin@local') {
      setChecked(true);
      return;
    }
    const token = getAdminAccessToken();
    if (token && !isAuthenticated) {
      fetchProfile().finally(() => setChecked(true));
    } else {
      setChecked(true);
    }
  }, [fetchProfile, isAuthenticated, admin]);

  if (!checked || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-600 text-sm">
        Verifying admin session...
      </div>
    );
  }

  if (!isAuthenticated || !admin) {
    return <Navigate to="/admin/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
};

export default ProtectedAdminRoute;
