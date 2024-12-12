import { toast } from 'react-hot-toast';
import { CheckCircleIcon, XCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';

interface NotificationOptions {
  title: string;
  message: string;
  type?: 'success' | 'error' | 'info';
  duration?: number;
}

export const showNotification = (options: NotificationOptions) => {
  const { title, message, type = 'info', duration = 3000 } = options;

  const toastOptions = {
    duration,
    style: {
      borderRadius: '8px',
      backgroundColor: getBackgroundColor(type),
      color: getTextColor(type),
    },
  };

  toast.custom(
    <div className="flex items-center space-x-3 p-4">
      {getIcon(type)}
      <div>
        <p className="font-medium">{title}</p>
        <p className="text-sm">{message}</p>
      </div>
    </div>,
    toastOptions
  );
};

const getBackgroundColor = (type: NotificationOptions['type']) => {
  switch (type) {
    case 'success':
      return '#10B981';
    case 'error':
      return '#EF4444';
    default:
      return '#3B82F6';
  }
};

const getTextColor = (type: NotificationOptions['type']) => {
  switch (type) {
    case 'success':
    case 'error':
      return '#FFFFFF';
    default:
      return '#1F2937';
  }
};

const getIcon = (type: NotificationOptions['type']) => {
  switch (type) {
    case 'success':
      return <CheckCircleIcon className="h-6 w-6 text-green-500" />;
    case 'error':
      return <XCircleIcon className="h-6 w-6 text-red-500" />;
    default:
      return <InformationCircleIcon className="h-6 w-6 text-blue-500" />;
  }
};