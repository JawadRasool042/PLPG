import React from 'react';
import clsx from 'clsx';

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  accent?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'slate';
}

const iconRingMap: Record<NonNullable<StatCardProps['accent']>, string> = {
  indigo: 'bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100',
  emerald: 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100',
  amber: 'bg-amber-50 text-amber-600 ring-1 ring-amber-100',
  rose: 'bg-rose-50 text-rose-600 ring-1 ring-rose-100',
  slate: 'bg-slate-50 text-slate-600 ring-1 ring-slate-200',
};

const trendColorMap: Record<NonNullable<StatCardProps['trendDirection']>, string> = {
  up: 'text-emerald-600',
  down: 'text-rose-600',
  neutral: 'text-slate-500',
};

const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  trend,
  trendDirection = 'neutral',
  icon,
  accent = 'indigo',
}) => {
  return (
    <div className="group relative rounded-xl border border-slate-200 bg-white p-5 shadow-xs hover:shadow-md hover:border-slate-300 transition-all duration-200">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-semibold tracking-wider text-slate-500 uppercase">
            {label}
          </p>
          <p className="text-2xl sm:text-[28px] font-semibold text-slate-900 mt-2 tracking-tight tabular-nums leading-none">
            {value}
          </p>
          {trend && (
            <p className={clsx('text-xs font-medium mt-2.5', trendColorMap[trendDirection])}>
              {trend}
            </p>
          )}
        </div>
        {icon && (
          <div
            className={clsx(
              'h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105',
              iconRingMap[accent]
            )}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatCard;
