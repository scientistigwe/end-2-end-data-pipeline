import { toast } from 'react-hot-toast';
import {
  CheckCircle,
  XCircle,
  Info,
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/common/utils';

type NotificationType = 'success' | 'error' | 'info' | 'warning';

interface NotificationOptions {
  title: string;
  message: string;
  type?: NotificationType;
  duration?: number;
  position?: 'top-right' | 'top-center' | 'bottom-right' | 'bottom-center';
  action?: {
    label: string;
    onClick: () => void;
  };
}

const typeConfig = {
  success: {
    icon: CheckCircle,
    bgColor: 'bg-green-50',
    textColor: 'text-green-800',
    borderColor: 'border-green-200',
    iconColor: 'text-green-500'
  },
  error: {
    icon: XCircle,
    bgColor: 'bg-red-50',
    textColor: 'text-red-800',
    borderColor: 'border-red-200',
    iconColor: 'text-red-500'
  },
  warning: {
    icon: AlertTriangle,
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-800',
    borderColor: 'border-yellow-200',
    iconColor: 'text-yellow-500'
  },
  info: {
    icon: Info,
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-800',
    borderColor: 'border-blue-200',
    iconColor: 'text-blue-500'
  }
};

export const showNotification = (options: NotificationOptions) => {
  const {
    title,
    message,
    type = 'info',
    duration = 3000,
    position = 'top-right',
    action
  } = options;

  const config = typeConfig[type];
  const Icon = config.icon;

  // Determine toast position
  const positionOptions = {
    'top-right': { position: 'top-right' },
    'top-center': { position: 'top-center' },
    'bottom-right': { position: 'bottom-right' },
    'bottom-center': { position: 'bottom-center' }
  }[position];

  toast.custom(
    (t) => (
      <div
        className={cn(
          "max-w-md w-full shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 overflow-hidden",
          config.bgColor,
          config.borderColor,
          config.textColor
        )}
      >
        <div className="p-4 w-full">
          <div className="flex items-start">
            {/* Icon */}
            <div className="flex-shrink-0">
              <Icon className={cn("h-6 w-6", config.iconColor)} />
            </div>

            {/* Content */}
            <div className="ml-3 w-0 flex-1 pt-0.5">
              <p className="text-sm font-medium">{title}</p>
              <p className="mt-1 text-sm">{message}</p>

              {/* Optional Action */}
              {action && (
                <div className="mt-3 flex space-x-2">
                  <button
                    onClick={() => {
                      action.onClick();
                      toast.dismiss(t.id);
                    }}
                    className={cn(
                      "bg-white rounded-md text-sm font-medium px-3 py-2 inline-flex",
                      "hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2",
                      config.textColor
                    )}
                  >
                    {action.label}
                  </button>
                </div>
              )}
            </div>

            {/* Close Button */}
            <div className="ml-4 flex-shrink-0 flex">
              <button
                onClick={() => toast.dismiss(t.id)}
                className={cn(
                  "bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500",
                  "focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                )}
              >
                <span className="sr-only">Close</span>
                <XCircle className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    ),
    {
      duration,
      position: positionOptions.position,
      // Prevent multiple toasts of the same type
      id: `${type}-${title}`,
      // Custom enter/exit animations
      className: '!p-0 !m-0',
      enter: 'animate-fade-in-up',
      exit: 'animate-fade-out-down'
    }
  );
};

// Convenience methods for each notification type
export const successNotification = (options: Omit<NotificationOptions, 'type'>) =>
  showNotification({ ...options, type: 'success' });

export const errorNotification = (options: Omit<NotificationOptions, 'type'>) =>
  showNotification({ ...options, type: 'error' });

export const infoNotification = (options: Omit<NotificationOptions, 'type'>) =>
  showNotification({ ...options, type: 'info' });

export const warningNotification = (options: Omit<NotificationOptions, 'type'>) =>
  showNotification({ ...options, type: 'warning' });