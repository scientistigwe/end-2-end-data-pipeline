// src/utils/helpers/dateUtils.ts

/**
 * Formats a date string into a human-readable format
 * @param dateString - ISO date string to format
 * @returns Formatted date string
 */
export const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      }).format(date);
    } catch (error) {
      console.error('Error formatting date:', error);
      return dateString; // Return original string if parsing fails
    }
  };
  
  /**
   * Gets a date string for N days ago
   * @param days - Number of days to subtract from current date
   * @returns ISO date string
   */
  export const getDaysAgo = (days: number): string => {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return date.toISOString();
  };
  
  /**
   * Gets the current date as an ISO string
   * @returns Current date as ISO string
   */
  export const getCurrentDate = (): string => {
    return new Date().toISOString();
  };
  
  /**
   * Checks if a date string is valid
   * @param dateString - Date string to validate
   * @returns Whether the date string is valid
   */
  export const isValidDate = (dateString: string): boolean => {
    const date = new Date(dateString);
    return date instanceof Date && !isNaN(date.getTime());
  };