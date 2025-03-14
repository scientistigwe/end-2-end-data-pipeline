// src/auth/types/errors.ts
export class AuthError extends Error {
    constructor(
        message: string,
        public readonly code?: string,
        public readonly status?: number,
        public readonly details?: Record<string, any>
    ) {
        super(message);
        this.name = 'AuthError';
    }
}