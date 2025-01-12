// frontend\src\auth\pages\LoginPage.tsx
import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { useLocation, useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { LoginForm } from "../components/LoginForm";
import type { LoginCredentials } from "../types/auth";
import { useAuth } from "../hooks/useAuth";

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const from = (location.state as any)?.from?.pathname || "/dashboard";

  const handleLogin = async (credentials: LoginCredentials) => {
    try {
      await login(credentials);
      navigate(from, { replace: true });
    } catch (error) {
      throw error;
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
          <LogIn className="w-8 h-8 text-primary" />
        </motion.div>

        <h2 className="text-3xl font-bold tracking-tight text-foreground">
          Welcome Back
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Sign in to continue to your account
        </p>
      </div>

      <LoginForm onSubmit={handleLogin} />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="text-center text-sm text-muted-foreground"
      >
        Don't have an account?{" "}
        <Link
          to="/register"
          className="font-medium text-primary hover:text-primary/90 transition-colors"
        >
          Create a new account
        </Link>
      </motion.div>
    </motion.div>
  );
};

export default LoginPage;