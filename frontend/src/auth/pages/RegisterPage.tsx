// auth/pages/RegisterPage.tsx
import React from "react";
import { motion } from "framer-motion";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { UserPlus } from "lucide-react";
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
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-md mx-auto space-y-6 p-4"
    >
      <div className="text-center">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{
            type: "spring",
            stiffness: 300,
            damping: 20
          }}
          className="inline-flex items-center justify-center bg-primary/10 p-4 rounded-full mb-4"
        >
          <UserPlus className="w-8 h-8 text-primary" />
        </motion.div>

        <h2 className="text-3xl font-bold tracking-tight text-foreground">
          Create Your Account
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Join our platform and unlock powerful data capabilities
        </p>
      </div>

      <RegisterForm
        onSubmit={handleRegister}
        isLoading={isRegistering}
      />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="text-center text-sm text-muted-foreground"
      >
        Already have an account?{" "}
        <Link
          to="/login"
          className="font-medium text-primary hover:text-primary/90 transition-colors"
        >
          Sign in to your account
        </Link>
      </motion.div>
    </motion.div>
  );
};

export default RegisterPage;