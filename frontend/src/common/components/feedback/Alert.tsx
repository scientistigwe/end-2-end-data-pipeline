// src/common/components/feedback/Alert.tsx
import React from 'react';
import { cn } from '../../utils/cn';
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import {
  Alert as AlertUI,
  AlertTitle,
  AlertDescription,
} from '../../components/ui/alert';

type AlertVariant = 'default' | 'destructive' | 'success' | 'warning' | 'info';

interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  className?: string;
  showIcon?: boolean;
}

export const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  className = '',
  showIcon = true
}) => {
  const variantStyles: Record<AlertVariant, { icon: React.ReactNode }> = {
    default: {
      icon: <Info className="h-4 w-4" />
    },
    info: {
      icon: <Info className="h-4 w-4" />
    },
    success: {
      icon: <CheckCircle className="h-4 w-4" />
    },
    warning: {
      icon: <AlertTriangle className="h-4 w-4" />
    },
    destructive: {
      icon: <AlertCircle className="h-4 w-4" />
    }
  };

  return (
    <AlertUI variant={variant} className={cn(className)}>
      {showIcon && variantStyles[variant].icon}
      <div>
        {title && <AlertTitle>{title}</AlertTitle>}
        <AlertDescription>{children}</AlertDescription>
      </div>
    </AlertUI>
  );
};