// common/utils/storage.ts
export class StorageUtils {
    static setItem(key: string, value: unknown): void {
      localStorage.setItem(key, JSON.stringify(value));
    }
  
    static getItem<T>(key: string): T | null {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    }
  
    static removeItem(key: string): void {
      localStorage.removeItem(key);
    }
  }
  
  