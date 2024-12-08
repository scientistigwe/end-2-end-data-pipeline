// src/auth/routes/authRoutes.ts
import { RouteObject } from 'react-router-dom';
import { AuthLayout } from '../components/AuthLayout';
import { AuthMiddleware } from '../components/middleware/AuthMiddleware';
import { 
  LoginPage,
  RegisterPage,
  ForgotPasswordPage,
} from '../pages';
import { AUTH_ROUTES } from '../constants';

export const authRoutes: RouteObject[] = [
  {
    element: <AuthLayout />,
    children: [
      {
        path: AUTH_ROUTES.LOGIN,
        element: (
          <AuthMiddleware requireAuth={false}>
            <LoginPage />
          </AuthMiddleware>
        ),
      },
      {
        path: AUTH_ROUTES.REGISTER,
        element: (
          <AuthMiddleware requireAuth={false}>
            <RegisterPage />
          </AuthMiddleware>
        ),
      },
      {
        path: AUTH_ROUTES.FORGOT_PASSWORD,
        element: (
          <AuthMiddleware requireAuth={false}>
            <ForgotPasswordPage />
          </AuthMiddleware>
        ),
      }
    ],
  }
];

