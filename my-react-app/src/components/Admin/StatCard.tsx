import React from 'react';
import clsx from 'clsx';

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: string;
  icon?: React.ReactNode;
  accent?: 'indigo' | 'emerald' | 'amber' | 'rose';
}

const accentMap: Record<NonNullable<StatCardProps['accent']>, string> = {
  indigo: 'bg-indigo-50 border-indigo-100',
  emerald: 'bg-emerald-50 border-emerald-100',
  amber: 'bg-amber-50 border-amber-100',
  rose: 'bg-rose-50 border-rose-100',
};

const iconColorMap: Record<NonNullable<StatCardProps['accent']>, string> = {
  indigo: 'text-indigo-600',
  emerald: 'text-emerald-600',
  amber: 'text-amber-600',
  rose: 'text-rose-600',
};

const StatCard: React.FC<StatCardProps> = ({ label, value, trend, icon, accent = 'indigo' }) => {
  return (
    <div className={clsx('rounded-2xl border-2 bg-white p-6 shadow-sm hover:shadow-md transition-all', accentMap[accent])}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-600">{label}</p>
          <p className="text-3xl font-bold text-slate-900 mt-2">{value}</p>
          {trend && <p className="text-xs text-slate-500 mt-2">{trend}</p>}
        </div>
        {icon && (
          <div className={clsx('h-12 w-12 rounded-xl bg-white/80 flex items-center justify-center shadow-inner', iconColorMap[accent])}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatCard;
