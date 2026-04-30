import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useStore } from '../store/useStore';

interface ProtectedInterestRouteProps {
  children?: React.ReactNode;
}

/**
 * Protected route component that ensures user is logged in
 * before accessing the interest assessment page.
 * Redirects to login if not authenticated.
 */
const ProtectedInterestRoute: React.FC<ProtectedInterestRouteProps> = ({ children }) => {
  const { isAuthenticated, user } = useStore();
  const location = useLocation();

  // If not authenticated, redirect to login with return URL
  if (!isAuthenticated || !user) {
    return (
      <Navigate 
        to="/login" 
        state={{ from: location, message: 'Please log in to access the personalized learning path checker.' }} 
        replace 
      />
    );
  }

  // User is authenticated, render the protected content
  return children ? <>{children}</> : <Outlet />;
};

export default ProtectedInterestRoute;
