// auth/types/index.ts
// Core auth types
export type {
    AuthStatus,
    AuthTokens,
    AuthState,
    LoginCredentials,
    RegisterData,
    PasswordOperations,
    SessionInfo,
    AuthPreferences,
    AuthEventType,
    AuthEvent
  } from './auth';
  
  // Permission types
  export type {
    ResourceType,
    ActionType,
    Permission,
    PermissionCheck
  } from './permissions';
  export { 
    CORE_PERMISSIONS,
    isValidPermission,
    formatPermission 
  } from './permissions';
  
  // Role types
  export type {
    RoleType,
    Role,
    RoleCreateData,
    RoleUpdateData,
    RoleAudit,
    RoleMutationResponse
  } from './roles';
  
  // Admin types
  export type {
    AdminBulkAction,
    AdminUserFilters,
    AdminPaginationParams,
    AdminAuditLog,
    AdminStats
  } from './admin';
  
  // API types
  export type {
    AuthApiResponse,
    LoginResponse,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    PasswordResetRequest,
    RoleUpdateRequest,
    AuthApiError,
    TokenValidationResponse,
    EmailVerificationResponse,
    PasswordChangeResponse
  } from './api';
  
  // RBAC types
  export type {
    RBACRole,
    RoleHierarchy,
    RolePermissions,
    RBACConfig,
    RBACCheckResult,
    RBACOperations
  } from './rbac';
  export { 
    DEFAULT_ROLE_HIERARCHY,
    rbacHelpers 
} from './rbac';
  

