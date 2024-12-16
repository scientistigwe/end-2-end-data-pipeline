// src/auth/pages/LoginPage.tsx
import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { LoginForm } from "../components/LoginForm";
import { AuthLayout } from "../components/AuthLayout";
import type { LoginCredentials } from "../types/auth";
import { useAuth } from "../hooks/useAuth";

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const from = (location.state as any)?.from?.pathname || "/";

  const handleLogin = async (credentials: LoginCredentials) => {
    try {
      await login(credentials);
      navigate(from, { replace: true });
    } catch (error) {
      // Error handling is done in the form component
      throw error;
    }
  };

  return (
    <AuthLayout>
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Sign in to your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Or{" "}
          <a
            href="/register"
            className="font-medium text-blue-600 hover:text-blue-500"
          >
            create a new account
          </a>
        </p>
      </div>
      <LoginForm onSubmit={handleLogin} />
    </AuthLayout>
  );
};

export default LoginPage;
