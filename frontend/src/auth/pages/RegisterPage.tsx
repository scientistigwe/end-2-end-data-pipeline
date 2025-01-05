// auth/pages/RegisterPage.tsx
import React from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { RegisterForm } from "../components/RegisterForm";
import { useAuth } from "../hooks/useAuth";
import type { RegisterData } from "../types/auth";

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { register, isRegistering } = useAuth();

  const from = (location.state as any)?.from?.pathname || "/dashboard";

  const handleRegister = async (data: RegisterData) => {
    try {
      await register(data);
      // After successful registration and auto-login, navigate to dashboard
      navigate(from, { replace: true });
    } catch (error: any) {
      // Let the form handle the error display
      if (error.response?.status === 409) {
        throw new Error("An account with this email already exists");
      }
      if (error.response?.data?.error?.details) {
        throw new Error(error.response.data.error.details);
      }
      throw new Error(
        error.message || "Registration failed. Please try again."
      );
    }
  };

  return (
    <div className="w-full">
      <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-foreground">
        Create your account
      </h2>
      <p className="mt-2 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link
          to="/login"
          className="font-medium text-primary hover:text-primary/90"
        >
          Sign in
        </Link>
      </p>
      <div className="mt-8">
        <RegisterForm onSubmit={handleRegister} isLoading={isRegistering} />
      </div>
    </div>
  );
};

export default RegisterPage;
