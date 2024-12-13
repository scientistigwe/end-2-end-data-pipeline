// auth/routes/authRoutes.tsx
import { lazy, Suspense } from 'react';
import { RouteObject } from 'react-router-dom';
import { AuthLayout } from '../components/AuthLayout';
import { AuthGuard } from '../components/AuthGuard';
import { LoadingSpinner } from '@/common/components/navigation/LoadingSpinner';
import { ErrorBoundary } from '@/common/components/errors/ErrorBoundary';
import { AUTH_API_CONFIG } from '../api/config';

// Lazy loaded pages with proper naming and error boundaries
const LoginPage = lazy(() => 
  import('../pages/LoginPage').then(module => ({
    default: module.LoginPage
  }))
);

const RegisterPage = lazy(() => 
  import('../pages/RegisterPage').then(module => ({
    default: module.RegisterPage
  }))
);

const ForgotPasswordPage = lazy(() => 
  import('../pages/ForgotPasswordPage').then(module => ({
    default: module.ForgotPasswordPage
  }))
);

const ProfilePage = lazy(() => 
  import('../pages/ProfilePage').then(module => ({
    default: module.ProfilePage
  }))
);

// Wrapper for lazy loaded components with AuthLayout
const AuthPageWrapper: React.FC<{ component: React.ReactNode }> = ({ component }) => (
  <AuthLayout>
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        {component}
      </Suspense>
    </ErrorBoundary>
  </AuthLayout>
);

// Auth route configuration
export const authRoutes: RouteObject[] = [
  {
    path: AUTH_API_CONFIG.endpoints.LOGIN,
    element: (
      <AuthGuard requireAuth={false} redirectTo="/">
        <AuthPageWrapper component={<LoginPage />} />
      </AuthGuard>
    )
  },
  {
    path: AUTH_API_CONFIG.endpoints.REGISTER,
    element: (
      <AuthGuard requireAuth={false} redirectTo="/">
        <AuthPageWrapper component={<RegisterPage />} />
      </AuthGuard>
    )
  },
  {
    path: AUTH_API_CONFIG.endpoints.FORGOT_PASSWORD,
    element: (
      <AuthGuard requireAuth={false} redirectTo="/">
        <AuthPageWrapper component={<ForgotPasswordPage />} />
      </AuthGuard>
    )
  },
  {
    path: AUTH_API_CONFIG.endpoints.PROFILE,
    element: (
      <AuthGuard requireAuth>
        <AuthPageWrapper component={<ProfilePage />} />
      </AuthGuard>
    )
  }
];

// Type-safe route paths
export const AUTH_PATHS = {
  LOGIN: AUTH_API_CONFIG.endpoints.LOGIN,
  REGISTER: AUTH_API_CONFIG.endpoints.REGISTER,
  FORGOT_PASSWORD: AUTH_API_CONFIG.endpoints.FORGOT_PASSWORD,
  PROFILE: AUTH_API_CONFIG.endpoints.PROFILE,
} as const;

// Utility for generating auth route paths
export const getAuthPath = (path: keyof typeof AUTH_PATHS) => AUTH_PATHS[path];