// common/utils/date/dateUtils.ts

export interface DateFormatOptions extends Intl.DateTimeFormatOptions {
  includeTime?: boolean;
}

interface TimeAddition {
  days?: number;
  hours?: number;
  minutes?: number;
  seconds?: number;
}

export const dateUtils = {
  /**
   * Format a date into a human-readable string
   * @param date - The date to format
   * @param options - Optional formatting options
   * @returns Formatted date string
   */
  formatDate(date: string | Date, options?: DateFormatOptions): string {
    try {
      const dateObj = new Date(date);
      const defaultOptions: DateFormatOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        ...(options?.includeTime ? {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true
        } : {}),
        ...options
      };

      return new Intl.DateTimeFormat('en-US', defaultOptions).format(dateObj);
    } catch (error) {
      console.error('Error formatting date:', error);
      return String(date);
    }
  },

  /**
   * Format relative time (e.g., "2 hours ago")
   * @param date - The date to format relative to now
   * @returns Formatted relative time string
   */
  formatRelativeTime(date: string | Date): string {
    try {
      const now = new Date();
      const past = new Date(date);
      const diffMs = now.getTime() - past.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 60) {
        return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
      }
      if (diffHours < 24) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
      }
      if (diffDays < 7) {
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
      }
      return this.formatDate(past);
    } catch {
      return String(date);
    }
  },

  /**
   * Format duration in seconds to human-readable string
   * @param seconds - Number of seconds to format
   * @returns Formatted duration string
   */
  formatDuration(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
      return `${days} day${days !== 1 ? 's' : ''}`;
    }
    if (hours > 0) {
      return `${hours} hour${hours !== 1 ? 's' : ''}`;
    }
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  },

  /**
   * Get date for N days ago
   * @param days - Number of days to subtract
   * @returns Date object for N days ago
   */
  getDaysAgo(days: number): Date {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return date;
  },

  /**
   * Get current date
   * @returns Current date object
   */
  getCurrentDate(): Date {
    return new Date();
  },

  /**
   * Check if a date string is valid
   * @param dateString - The date string to validate
   * @returns Boolean indicating if date is valid
   */
  isValidDate(dateString: string): boolean {
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date.getTime());
  },

  /**
   * Get start of day
   * @param date - Optional date (defaults to current date)
   * @returns Date object set to start of day
   */
  getStartOfDay(date: Date = new Date()): Date {
    return new Date(date.setHours(0, 0, 0, 0));
  },

  /**
   * Get end of day
   * @param date - Optional date (defaults to current date)
   * @returns Date object set to end of day
   */
  getEndOfDay(date: Date = new Date()): Date {
    return new Date(date.setHours(23, 59, 59, 999));
  },

  /**
   * Add time to date
   * @param date - Base date to add time to
   * @param time - Object containing time units to add
   * @returns New date with added time
   */
  addTime(date: Date, { days = 0, hours = 0, minutes = 0, seconds = 0 }: TimeAddition): Date {
    const newDate = new Date(date);
    newDate.setDate(newDate.getDate() + days);
    newDate.setHours(newDate.getHours() + hours);
    newDate.setMinutes(newDate.getMinutes() + minutes);
    newDate.setSeconds(newDate.getSeconds() + seconds);
    return newDate;
  },

  /**
   * Format date range
   * @param startDate - The start date of the range
   * @param endDate - The end date of the range
   * @param options - Optional formatting options
   * @returns Formatted date range string
   */
  formatDateRange(startDate: Date, endDate: Date, options?: DateFormatOptions): string {
    const start = this.formatDate(startDate, options);
    const end = this.formatDate(endDate, options);
    return `${start} - ${end}`;
  },

  /**
   * Compare dates
   * @param date1 - First date to compare
   * @param date2 - Second date to compare
   * @returns Negative if date1 < date2, positive if date1 > date2, 0 if equal
   */
  compareDates(date1: Date, date2: Date): number {
    return date1.getTime() - date2.getTime();
  },

  /**
   * Check if date is between range
   * @param date - Date to check
   * @param startDate - Start of range
   * @param endDate - End of range
   * @returns Boolean indicating if date is within range
   */
  isDateBetween(date: Date, startDate: Date, endDate: Date): boolean {
    return date >= startDate && date <= endDate;
  },

  /**
   * Get the quarter number for a given date
   * @param date - Optional date (defaults to current date)
   * @returns Quarter number (1-4)
   */
  getQuarter(date: Date = new Date()): number {
    try {
      return Math.floor(date.getMonth() / 3) + 1;
    } catch (error) {
      console.error('Error getting quarter:', error);
      return 0;
    }
  },

  /**
   * Get start date of quarter
   * @param date - Optional date (defaults to current date)
   * @returns Date object set to start of quarter
   */
  getStartOfQuarter(date: Date = new Date()): Date {
    try {
      const quarter = this.getQuarter(date);
      const startMonth = (quarter - 1) * 3;
      const startOfQuarter = new Date(date.getFullYear(), startMonth, 1);
      return this.getStartOfDay(startOfQuarter);
    } catch (error) {
      console.error('Error getting start of quarter:', error);
      return date;
    }
  },

  /**
   * Get end date of quarter
   * @param date - Optional date (defaults to current date)
   * @returns Date object set to end of quarter
   */
  getEndOfQuarter(date: Date = new Date()): Date {
    try {
      const quarter = this.getQuarter(date);
      const endMonth = quarter * 3 - 1;
      const endOfQuarter = new Date(date.getFullYear(), endMonth + 1, 0);
      return this.getEndOfDay(endOfQuarter);
    } catch (error) {
      console.error('Error getting end of quarter:', error);
      return date;
    }
  },

      /**
     * Format duration from milliseconds with detailed units
     * @param ms - Duration in milliseconds
     * @returns Formatted duration string with units (e.g., "2h 30m 15s")
     */
    formatDetailedDuration(ms: number): string {
      try {
        if (ms < 1000) return `${ms}ms`;
        
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
  
        if (hours > 0) {
          return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        }
        if (minutes > 0) {
          return `${minutes}m ${seconds % 60}s`;
        }
        return `${seconds}s`;
      } catch (error) {
        console.error('Error formatting detailed duration:', error);
        return String(ms) + 'ms';
      }
    },
  
    /**
     * Format time ago with short units
     * @param date - Date to format
     * @returns Short format relative time (e.g., "2h ago")
     */
    formatTimeAgoShort(date: string | Date): string {
      try {
        const now = new Date();
        const past = new Date(date);
        const diffMs = now.getTime() - past.getTime();
        
        const diffMinutes = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);
  
        if (diffDays > 0) return `${diffDays}d ago`;
        if (diffHours > 0) return `${diffHours}h ago`;
        if (diffMinutes > 0) return `${diffMinutes}m ago`;
        return 'just now';
      } catch (error) {
        console.error('Error formatting short time ago:', error);
        return String(date);
      }
    },
};