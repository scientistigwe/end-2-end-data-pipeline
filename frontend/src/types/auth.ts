// src/types/auth.ts
import { UserRole } from './common';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  permissions: string[];
}

export interface AuthPayload {
  token: string;
  refreshToken: string;
  user: User;
}
