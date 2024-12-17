import React from "react";
import { useNavigate, Link } from "react-router-dom";
import { RegisterForm } from "../components/RegisterForm";
import { AuthLayout } from "../components/AuthLayout";
import { useAuth } from "../hooks/useAuth";
import type { RegisterData } from "../types/auth";

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const handleRegister = async (data: RegisterData) => {
    try {
      await register(data);
      navigate("/login", {
        replace: true,
        state: { message: "Registration successful! Please log in." },
      });
    } catch (error) {
      throw error;
    }
  };

  return (
    <AuthLayout>
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
        <RegisterForm onSubmit={handleRegister} />
      </div>
    </AuthLayout>
  );
};

export default RegisterPage;
