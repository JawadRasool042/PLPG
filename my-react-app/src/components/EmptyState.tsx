import React from 'react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction
}) => {
  const defaultIcon = (
    <svg className="w-16 h-16 sm:w-20 sm:h-20 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
    </svg>
  );

  return (
    <div className="min-h-[400px] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-md w-full text-center">
        <div className="w-20 h-20 sm:w-24 sm:h-24 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-6 sm:mb-8 transform transition-transform duration-300 hover:scale-110">
          {icon || defaultIcon}
        </div>
        
        <h3 className="text-xl sm:text-2xl font-bold text-slate-900 mb-3 sm:mb-4">
          {title}
        </h3>
        
        <p className="text-sm sm:text-base text-slate-600 mb-6 sm:mb-8 leading-relaxed max-w-sm mx-auto">
          {description}
        </p>
        
        {(actionLabel || secondaryActionLabel) && (
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
            {actionLabel && onAction && (
              <button
                onClick={onAction}
                className="inline-flex items-center justify-center px-6 sm:px-8 py-3 sm:py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-semibold hover:from-indigo-700 hover:to-purple-700 transform transition-all duration-200 hover:scale-105 shadow-lg hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 text-sm sm:text-base"
              >
                {actionLabel}
                <svg className="ml-2 w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
            )}
            
            {secondaryActionLabel && onSecondaryAction && (
              <button
                onClick={onSecondaryAction}
                className="inline-flex items-center justify-center px-6 sm:px-8 py-3 sm:py-4 bg-white text-slate-700 border-2 border-slate-300 rounded-xl font-semibold hover:bg-slate-50 hover:border-slate-400 transform transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 text-sm sm:text-base"
              >
                {secondaryActionLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default EmptyState;
