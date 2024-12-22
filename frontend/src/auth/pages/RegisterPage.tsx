// frontend\src\auth\pages\RegisterPage.tsx
import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { RegisterForm } from "../components/RegisterForm";
import { authApi } from "../api/authApi";
import type { RegisterData } from "../types/auth";

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const handleRegister = async (data: RegisterData) => {
    setIsLoading(true);
    try {
      await authApi.register(data);
      navigate("/login", {
        replace: true,
        state: { message: "Registration successful! Please log in." },
      });
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
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
        <RegisterForm onSubmit={handleRegister} isLoading={isLoading} />
      </div>
    </div>
  );
};

export default RegisterPage;
