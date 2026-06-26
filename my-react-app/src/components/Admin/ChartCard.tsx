import React from 'react';
import clsx from 'clsx';

interface ChartCardProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
}

const ChartCard: React.FC<ChartCardProps> = ({
  title,
  description,
  action,
  children,
  className,
  contentClassName,
}) => {
  return (
    <div
      className={clsx(
        'rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden',
        className
      )}
    >
      <div className="px-5 py-4 border-b border-slate-100 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold text-slate-900 tracking-tight">{title}</h3>
          {description && (
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
          )}
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
      <div className={clsx('p-5', contentClassName)}>{children}</div>
    </div>
  );
};

export default ChartCard;
