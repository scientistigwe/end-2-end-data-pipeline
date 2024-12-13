// common/utils/storage/storageUtils.ts
type StorageType = 'local' | 'session';

interface StorageOptions {
  storage?: StorageType;
  prefix?: string;
  encrypt?: boolean;
}

class StorageManager {
  private static instance: StorageManager;
  private readonly defaultPrefix: string = 'app';

  private constructor() {}

  static getInstance(): StorageManager {
    if (!StorageManager.instance) {
      StorageManager.instance = new StorageManager();
    }
    return StorageManager.instance;
  }

  /**
   * Set item in storage
   */
  setItem<T>(
    key: string, 
    value: T, 
    options: StorageOptions = {}
  ): void {
    const { 
      storage = 'local',
      prefix = this.defaultPrefix,
      encrypt = false
    } = options;

    const storageKey = this.createKey(key, prefix);
    const serializedValue = JSON.stringify(value);
    const finalValue = encrypt ? 
      this.encrypt(serializedValue) : 
      serializedValue;

    this.getStorage(storage).setItem(storageKey, finalValue);
  }

  /**
   * Get item from storage
   */
  getItem<T>(
    key: string, 
    options: StorageOptions = {}
  ): T | null {
    const { 
      storage = 'local',
      prefix = this.defaultPrefix,
      encrypt = false
    } = options;

    const storageKey = this.createKey(key, prefix);
    const value = this.getStorage(storage).getItem(storageKey);

    if (!value) return null;

    try {
      const decryptedValue = encrypt ? 
        this.decrypt(value) : 
        value;
      return JSON.parse(decryptedValue);
    } catch {
      return null;
    }
  }

  /**
   * Remove item from storage
   */
  removeItem(
    key: string, 
    options: StorageOptions = {}
  ): void {
    const { 
      storage = 'local',
      prefix = this.defaultPrefix 
    } = options;

    const storageKey = this.createKey(key, prefix);
    this.getStorage(storage).removeItem(storageKey);
  }

  /**
   * Clear all items from storage
   */
  clear(
    options: StorageOptions = {}
  ): void {
    const { 
      storage = 'local',
      prefix = this.defaultPrefix 
    } = options;

    if (prefix) {
      this.clearWithPrefix(storage, prefix);
    } else {
      this.getStorage(storage).clear();
    }
  }

  /**
   * Get all keys from storage
   */
  keys(
    options: StorageOptions = {}
  ): string[] {
    const { 
      storage = 'local',
      prefix = this.defaultPrefix 
    } = options;

    const allKeys = Object.keys(this.getStorage(storage));
    return prefix ? 
      allKeys.filter(key => key.startsWith(`${prefix}:`)) :
      allKeys;
  }

  /**
   * Check if key exists in storage
   */
  hasItem(
    key: string,
    options: StorageOptions = {}
  ): boolean {
    const { 
      storage = 'local',
      prefix = this.defaultPrefix 
    } = options;

    const storageKey = this.createKey(key, prefix);
    return this.getStorage(storage).getItem(storageKey) !== null;
  }

  /**
   * Get storage size in bytes
   */
  getSize(
    options: StorageOptions = {}
  ): number {
    const { storage = 'local' } = options;
    let size = 0;
    const store = this.getStorage(storage);
    
    Object.keys(store).forEach(key => {
      const value = store.getItem(key);
      if (value) {
        size += key.length + value.length;
      }
    });

    return size;
  }

  private getStorage(type: StorageType): Storage {
    return type === 'local' ? localStorage : sessionStorage;
  }

  private createKey(key: string, prefix?: string): string {
    return prefix ? `${prefix}:${key}` : key;
  }

  private clearWithPrefix(storage: StorageType, prefix: string): void {
    const store = this.getStorage(storage);
    const keys = Object.keys(store)
      .filter(key => key.startsWith(`${prefix}:`));
    
    keys.forEach(key => store.removeItem(key));
  }

  private encrypt(value: string): string {
    // Simple base64 encoding for example
    // In production, use a proper encryption method
    return btoa(value);
  }

  private decrypt(value: string): string {
    // Simple base64 decoding for example
    // In production, use a proper decryption method
    return atob(value);
  }
}

export const storageUtils = StorageManager.getInstance();