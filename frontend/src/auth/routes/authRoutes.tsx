// src/auth/routes/authRoutes.ts
import { lazy } from "react";
import type { RouteConfig } from "@/common/types/routes";
import { AuthGuard } from "../components/AuthGuard";
import { AuthLayout } from "../components/AuthLayout";

// Lazy loaded pages
const LoginPage = lazy(() => import("../pages/LoginPage"));
const RegisterPage = lazy(() => import("../pages/RegisterPage"));
const ForgotPasswordPage = lazy(() => import("../pages/ForgotPasswordPage"));
const ProfilePage = lazy(() => import("../pages/ProfilePage"));

// Route paths configuration
export const AUTH_PATHS = {
  LOGIN: "/login",
  REGISTER: "/register",
  FORGOT_PASSWORD: "/forgot-password",
  PROFILE: "/profile",
} as const;

export type AuthPath = (typeof AUTH_PATHS)[keyof typeof AUTH_PATHS];

// Auth routes configuration
export const authRoutes: RouteConfig[] = [
  {
    path: AUTH_PATHS.LOGIN,
    element: LoginPage,
    layoutComponent: AuthLayout,
    guard: {
      component: AuthGuard,
      props: { requireAuth: false, redirectTo: "/" },
    },
  },
  {
    path: AUTH_PATHS.REGISTER,
    element: RegisterPage,
    layoutComponent: AuthLayout,
    guard: {
      component: AuthGuard,
      props: { requireAuth: false, redirectTo: "/" },
    },
  },
  {
    path: AUTH_PATHS.FORGOT_PASSWORD,
    element: ForgotPasswordPage,
    layoutComponent: AuthLayout,
    guard: {
      component: AuthGuard,
      props: { requireAuth: false, redirectTo: "/" },
    },
  },
  {
    path: AUTH_PATHS.PROFILE,
    element: ProfilePage,
    layoutComponent: AuthLayout,
    guard: {
      component: AuthGuard,
      props: { requireAuth: true },
    },
  },
];

// Helper function to get route path
export const getAuthPath = (path: keyof typeof AUTH_PATHS): AuthPath =>
  AUTH_PATHS[path];
