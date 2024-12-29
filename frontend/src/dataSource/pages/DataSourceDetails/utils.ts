// src/dataSource/pages/DataSourceDetails/utils.ts
export const formatBytes = (bytes: number, decimals = 2): string => {
    if (bytes === 0) return '0 Bytes';
  
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
    const i = Math.floor(Math.log(bytes) / Math.log(k));
  
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
  };
  
  export const formatDate = (date: string | undefined): string => {
    if (!date) return 'Never';
    return new Date(date).toLocaleString();
  };
  
  export const formatDuration = (milliseconds: number): string => {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
  
    if (days > 0) return `${days}d ${hours % 24}h`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };
  
  export const getStatusColor = (status: string): string => {
    const statusMap: Record<string, string> = {
      connected: 'text-green-500',
      disconnected: 'text-gray-500',
      error: 'text-red-500',
      connecting: 'text-yellow-500',
      validating: 'text-blue-500'
    };
    return statusMap[status.toLowerCase()] || 'text-gray-500';
  };