// src/auth/components/ForgotPasswordForm.tsx
import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, Mail, ArrowLeft } from "lucide-react";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/inputs/input";
import {
  Alert,
  AlertTitle,
  AlertDescription,
} from "@/common/components/ui/alert";
import { useAuth } from "../hooks/useAuth";
import { cn } from "@/common/utils";

export const ForgotPasswordForm: React.FC = () => {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [touched, setTouched] = useState(false);
  const navigate = useNavigate();
  const { forgotPassword } = useAuth();

  // Email validation
  const isValidEmail = useCallback((emailValue: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(emailValue);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);

    // Validate email before submission
    if (!isValidEmail(email)) {
      setError("Please enter a valid email address");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || "Failed to send reset instructions");
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEmail = e.target.value;
    setEmail(newEmail);

    // Clear any previous errors when user starts typing
    if (error) setError(null);
  };

  // Success State
  if (success) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-6 max-w-md mx-auto"
      >
        <Alert variant="success">
          <CheckCircle2 className="h-5 w-5" />
          <AlertTitle>Check Your Email</AlertTitle>
          <AlertDescription>
            We've sent password reset instructions to {email}
          </AlertDescription>
        </Alert>

        <div className="space-y-4">
          <Button
            variant="outline"
            className="w-full"
            onClick={() => navigate("/login")}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Return to Login
          </Button>
        </div>
      </motion.div>
    );
  }

  // Main Form
  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6 w-full max-w-md"
    >
      <div className="text-center">
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Forgot Your Password?
        </h2>
        <p className="text-muted-foreground">
          Enter your email to reset your password
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Error Alert */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Alert variant="destructive">
                <AlertCircle className="h-5 w-5" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Email Input */}
        <div className="space-y-2">
          <label
            htmlFor="email"
            className="block text-sm font-medium text-foreground flex justify-between items-center"
          >
            Email Address
            {touched &&
              email &&
              (isValidEmail(email) ? (
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-500" />
              ))}
          </label>
          <div className="relative">
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={handleEmailChange}
              className={cn(
                "w-full pl-10",
                touched && email && !isValidEmail(email)
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
              disabled={isLoading}
            />
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          </div>
          {touched && email && !isValidEmail(email) && (
            <p className="text-xs text-red-600 mt-1">
              Please enter a valid email address
            </p>
          )}
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          className="w-full group"
          disabled={isLoading || (touched && !isValidEmail(email))}
        >
          <motion.span
            initial={{ scale: 1 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300 }}
            className="flex items-center justify-center"
          >
            {isLoading ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Sending...
              </>
            ) : (
              "Send Reset Instructions"
            )}
          </motion.span>
        </Button>

        {/* Return to Login Link */}
        <div className="text-center">
          <Link
            to="/login"
            className="text-sm font-medium text-primary hover:text-primary/90 flex items-center justify-center"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Return to Login
          </Link>
        </div>
      </form>
    </motion.div>
  );
};
