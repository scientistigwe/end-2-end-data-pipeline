// common/types/user.ts
import type { BaseAuthUser } from './auth';

export type RoleType = 'admin' | 'manager' | 'user';

export interface User extends BaseAuthUser {
  department?: string;
  timezone?: string;
  locale?: string;
  phoneNumber?: string;
  // ... your flask_app-specific user properties
}