import React from 'react';

interface LoadingSkeletonProps {
  variant?: 'card' | 'text' | 'avatar' | 'button' | 'table';
  count?: number;
  className?: string;
}

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ 
  variant = 'card', 
  count = 1,
  className = '' 
}) => {
  const renderSkeleton = () => {
    switch (variant) {
      case 'card':
        return (
          <div className={`bg-white rounded-2xl p-6 sm:p-8 shadow-lg border border-slate-200 animate-pulse ${className}`}>
            <div className="flex items-start gap-4 mb-4">
              <div className="w-12 h-12 sm:w-14 sm:h-14 bg-slate-200 rounded-xl"></div>
              <div className="flex-1 space-y-3">
                <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                <div className="h-3 bg-slate-200 rounded w-1/2"></div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-slate-200 rounded"></div>
              <div className="h-3 bg-slate-200 rounded w-5/6"></div>
            </div>
          </div>
        );
      
      case 'text':
        return (
          <div className={`animate-pulse space-y-2 ${className}`}>
            <div className="h-4 bg-slate-200 rounded w-full"></div>
            <div className="h-4 bg-slate-200 rounded w-5/6"></div>
            <div className="h-4 bg-slate-200 rounded w-4/6"></div>
          </div>
        );
      
      case 'avatar':
        return (
          <div className={`animate-pulse ${className}`}>
            <div className="w-16 h-16 sm:w-20 sm:h-20 bg-slate-200 rounded-full"></div>
          </div>
        );
      
      case 'button':
        return (
          <div className={`animate-pulse ${className}`}>
            <div className="h-10 sm:h-12 bg-slate-200 rounded-lg w-full"></div>
          </div>
        );
      
      case 'table':
        return (
          <div className={`bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden animate-pulse ${className}`}>
            <div className="bg-slate-50 border-b border-slate-200 p-4">
              <div className="grid grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-4 bg-slate-200 rounded"></div>
                ))}
              </div>
            </div>
            <div className="divide-y divide-slate-200">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="p-4">
                  <div className="grid grid-cols-4 gap-4">
                    {[...Array(4)].map((_, j) => (
                      <div key={j} className="h-3 bg-slate-200 rounded"></div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <>
      {[...Array(count)].map((_, index) => (
        <React.Fragment key={index}>
          {renderSkeleton()}
        </React.Fragment>
      ))}
    </>
  );
};

export default LoadingSkeleton;
