import React from "react";
import { Link } from "react-router-dom";
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
      throw error;
    }
  };

  return (
    <AuthLayout>
      <div className="w-full">
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-foreground">
          Sign in to your account
        </h2>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          Or{" "}
          <Link
            to="/register"
            className="font-medium text-primary hover:text-primary/90"
          >
            create a new account
          </Link>
        </p>
        <LoginForm onSubmit={handleLogin} />
      </div>
    </AuthLayout>
  );
};

export default LoginPage;
