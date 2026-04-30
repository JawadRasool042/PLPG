import React from 'react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  onGoBack?: () => void;
  showRetry?: boolean;
  showGoBack?: boolean;
  icon?: 'error' | 'warning' | 'notFound';
}

const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = 'We encountered an error. Please try again.',
  onRetry,
  onGoBack,
  showRetry = true,
  showGoBack = true,
  icon = 'error'
}) => {
  const getIcon = () => {
    switch (icon) {
      case 'error':
        return (
          <svg className="w-12 h-12 sm:w-16 sm:h-16 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="w-12 h-12 sm:w-16 sm:h-16 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'notFound':
        return (
          <svg className="w-12 h-12 sm:w-16 sm:h-16 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  const getIconBg = () => {
    switch (icon) {
      case 'error':
        return 'bg-red-100';
      case 'warning':
        return 'bg-amber-100';
      case 'notFound':
        return 'bg-slate-100';
    }
  };

  return (
    <div className="min-h-[400px] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-6 sm:p-8 text-center transform transition-all duration-300 hover:shadow-2xl">
        <div className={`w-16 h-16 sm:w-20 sm:h-20 ${getIconBg()} rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6 transform transition-transform duration-300 hover:scale-110`}>
          {getIcon()}
        </div>
        
        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-2 sm:mb-3">
          {title}
        </h2>
        
        <p className="text-sm sm:text-base text-slate-600 mb-6 sm:mb-8 leading-relaxed">
          {message}
        </p>
        
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
          {showRetry && onRetry && (
            <button
              onClick={onRetry}
              className="flex-1 px-4 sm:px-6 py-2.5 sm:py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-semibold hover:from-indigo-700 hover:to-purple-700 transform transition-all duration-200 hover:scale-105 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 text-sm sm:text-base"
            >
              <svg className="inline-block w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Try Again
            </button>
          )}
          
          {showGoBack && onGoBack && (
            <button
              onClick={onGoBack}
              className="flex-1 px-4 sm:px-6 py-2.5 sm:py-3 bg-slate-100 text-slate-700 rounded-xl font-semibold hover:bg-slate-200 transform transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 text-sm sm:text-base"
            >
              <svg className="inline-block w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Go Back
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ErrorState;
