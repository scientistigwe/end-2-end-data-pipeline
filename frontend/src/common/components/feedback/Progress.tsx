// src/common/components/feedback/Progress.tsx
import React from 'react';
import { cn } from '../../utils/cn';

interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  showValue?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'error';
  className?: string;
  barClassName?: string;
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  max = 100,
  size = 'md',
  showValue = false,
  variant = 'default',
  className = '',
  barClassName = ''
}) => {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  };

  const variantClasses = {
    default: 'bg-primary',
    success: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500'
  };

  return (
    <div className="relative">
      <div
        className={cn(
          'w-full rounded-full bg-gray-200 dark:bg-gray-700',
          sizeClasses[size],
          className
        )}
      >
        <div
          className={cn(
            'rounded-full transition-all duration-300 ease-in-out',
            sizeClasses[size],
            variantClasses[variant],
            barClassName
          )}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
      {showValue && (
        <span className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          {percentage.toFixed(0)}%
        </span>
      )}
    </div>
  );
};