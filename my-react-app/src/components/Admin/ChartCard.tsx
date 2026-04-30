import React from 'react';
import clsx from 'clsx';

interface ChartCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

const ChartCard: React.FC<ChartCardProps> = ({ title, description, children, className }) => {
  return (
    <div className={clsx('rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden', className)}>
      <div className="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-slate-100">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        {description && <p className="text-sm text-slate-600 mt-1">{description}</p>}
      </div>
      <div className="p-6">
        {children}
      </div>
    </div>
  );
};

export default ChartCard;
