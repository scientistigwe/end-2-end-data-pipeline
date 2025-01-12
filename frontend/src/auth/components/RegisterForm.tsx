// src/auth/components/RegisterForm.tsx
import React, { useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { 
  AlertCircle, 
  CheckCircle2, 
  XCircle, 
  Eye, 
  EyeOff 
} from "lucide-react";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/inputs";
import { cn } from "@/common/utils";
import type { RegisterData } from "../types/auth";
import { isAuthError, getErrorMessage } from "../utils/errorHandlings";

interface RegisterFormProps {
  onSubmit: (data: RegisterData) => Promise<void>;
  isLoading?: boolean;
}

interface FormState extends RegisterData {
  confirmPassword: string;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({
  onSubmit,
  isLoading = false,
}) => {
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormState>({
    username: "",
    email: "",
    password: "",
    firstName: "",
    lastName: "",
    confirmPassword: "",
  });
  const [touched, setTouched] = useState<{
    [key: string]: boolean;
  }>({});
  const [showPassword, setShowPassword] = useState(false);

  // Validation rules
  const validationRules = useMemo(() => ({
    firstName: (value: string) => value.trim().length >= 2,
    lastName: (value: string) => value.trim().length >= 2,
    username: (value: string) => /^[a-zA-Z0-9_]{3,16}$/.test(value),
    email: (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
    password: (value: string) => {
      const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
      return passwordRegex.test(value);
    },
    confirmPassword: (value: string) => value === formData.password
  }), [formData.password]);

  // Validate individual field
  const isFieldValid = (name: string, value: string) => {
    return validationRules[name] ? validationRules[name](value) : true;
  };

  // Handle input changes
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Track touched state
    setTouched(prev => ({ ...prev, [name]: true }));

    // Clear any previous errors
    if (error) setError(null);
  }, [error]);

  // Validate entire form
  const validateForm = useCallback((): boolean => {
    // Check all fields
    const isValid = Object.keys(validationRules).every(key => 
      isFieldValid(key, formData[key])
    );

    if (!isValid) {
      setError("Please correct the errors in the form");
      return false;
    }

    return true;
  }, [formData, validationRules]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Mark all fields as touched
    setTouched(Object.keys(formData).reduce((acc, key) => ({
      ...acc, 
      [key]: true
    }), {}));

    if (!validateForm()) {
      return;
    }

    setError(null);

    try {
      const { confirmPassword, ...registrationData } = formData;
      await onSubmit(registrationData);
    } catch (err) {
      if (isAuthError(err)) {
        setError(getErrorMessage(err));
      } else {
        setError("Registration failed. Please try again.");
      }
    }
  };

  // Render validation icon
  const renderValidationIcon = (fieldName: string, value: string) => {
    if (!touched[fieldName]) return null;

    const isValid = isFieldValid(fieldName, value);
    return isValid ? (
      <CheckCircle2 className="w-5 h-5 text-green-500" />
    ) : (
      <XCircle className="w-5 h-5 text-red-500" />
    );
  };

  // Password strength indicator
  const getPasswordStrength = (password: string) => {
    if (password.length === 0) return null;
    if (password.length < 8) return "Weak";
    if (!validationRules.password(password)) return "Moderate";
    return "Strong";
  };

  const passwordStrength = getPasswordStrength(formData.password);

  return (
    <div className="w-full max-w-md mx-auto space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Error Alert */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg flex items-center space-x-2"
            >
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-sm">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Name Inputs */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label 
              htmlFor="firstName" 
              className="text-sm font-medium text-foreground flex justify-between items-center"
            >
              First Name
              {renderValidationIcon("firstName", formData.firstName)}
            </label>
            <Input
              id="firstName"
              name="firstName"
              type="text"
              required
              value={formData.firstName}
              onChange={handleChange}
              placeholder="John"
              autoComplete="given-name"
              className={cn(
                "w-full",
                touched.firstName && !isFieldValid("firstName", formData.firstName) 
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
              aria-invalid={touched.firstName && !isFieldValid("firstName", formData.firstName)}
            />
            {touched.firstName && !isFieldValid("firstName", formData.firstName) && (
              <p className="text-xs text-red-600 mt-1">
                First name must be at least 2 characters
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label 
              htmlFor="lastName" 
              className="text-sm font-medium text-foreground flex justify-between items-center"
            >
              Last Name
              {renderValidationIcon("lastName", formData.lastName)}
            </label>
            <Input
              id="lastName"
              name="lastName"
              type="text"
              required
              value={formData.lastName}
              onChange={handleChange}
              placeholder="Doe"
              autoComplete="family-name"
              className={cn(
                "w-full",
                touched.lastName && !isFieldValid("lastName", formData.lastName) 
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
              aria-invalid={touched.lastName && !isFieldValid("lastName", formData.lastName)}
            />
            {touched.lastName && !isFieldValid("lastName", formData.lastName) && (
              <p className="text-xs text-red-600 mt-1">
                Last name must be at least 2 characters
              </p>
            )}
          </div>
        </div>

        {/* Username Input */}
        <div className="space-y-2">
          <label 
            htmlFor="username" 
            className="text-sm font-medium text-foreground flex justify-between items-center"
          >
            Username
            {renderValidationIcon("username", formData.username)}
          </label>
          <Input
            id="username"
            name="username"
            type="text"
            required
            value={formData.username}
            onChange={handleChange}
            placeholder="johndoe"
            autoComplete="username"
            className={cn(
              "w-full",
              touched.username && !isFieldValid("username", formData.username) 
                ? "border-red-500 focus:ring-red-500"
                : "focus:border-blue-500 focus:ring-blue-500"
            )}
            aria-invalid={touched.username && !isFieldValid("username", formData.username)}
          />
          {touched.username && !isFieldValid("username", formData.username) && (
            <p className="text-xs text-red-600 mt-1">
              Username must be 3-16 characters, alphanumeric or underscore
            </p>
          )}
        </div>

        {/* Email Input */}
        <div className="space-y-2">
          <label 
            htmlFor="email" 
            className="text-sm font-medium text-foreground flex justify-between items-center"
          >
            Email
            {renderValidationIcon("email", formData.email)}
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            required
            value={formData.email}
            onChange={handleChange}
            placeholder="john.doe@example.com"
            autoComplete="email"
            className={cn(
              "w-full",
              touched.email && !isFieldValid("email", formData.email) 
                ? "border-red-500 focus:ring-red-500"
                : "focus:border-blue-500 focus:ring-blue-500"
            )}
            aria-invalid={touched.email && !isFieldValid("email", formData.email)}
          />
          {touched.email && !isFieldValid("email", formData.email) && (
            <p className="text-xs text-red-600 mt-1">
              Please enter a valid email address
            </p>
          )}
        </div>

        {/* Password Input */}
        <div className="space-y-2">
          <label 
            htmlFor="password" 
            className="text-sm font-medium text-foreground flex justify-between items-center"
          >
            Password
            {renderValidationIcon("password", formData.password)}
          </label>
          <div className="relative">
            <Input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              required
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              autoComplete="new-password"
              className={cn(
                "w-full pr-10",
                touched.password && !isFieldValid("password", formData.password) 
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
              aria-invalid={touched.password && !isFieldValid("password", formData.password)}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
              ) : (
                <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
              )}
            </button>
          </div>
          {touched.password && (
            <>
              {!isFieldValid("password", formData.password) && (
                <p className="text-xs text-red-600 mt-1">
                  Password must be 8+ characters, include uppercase, lowercase, number, and special character
                </p>
              )}
              {passwordStrength && (
                <div className="mt-1 flex items-center space-x-2">
                  <div 
                    className={cn(
                      "h-1.5 w-1/3 rounded-full",
                      passwordStrength === "Weak" && "bg-red-500",
                      passwordStrength === "Moderate" && "bg-yellow-500",
                      passwordStrength === "Strong" && "bg-green-500"
                    )}
                  />
                  <p className="text-xs text-gray-500">
                    {passwordStrength} password
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Confirm Password Input */}
        <div className="space-y-2">
          <label 
            htmlFor="confirmPassword" 
            className="text-sm font-medium text-foreground flex justify-between items-center"
          >
            Confirm Password
            {renderValidationIcon("confirmPassword", formData.confirmPassword)}
          </label>
          <Input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            required
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="••••••••"
            autoComplete="new-password"
            className={cn(
              "w-full",
              touched.confirmPassword && !isFieldValid("confirmPassword", formData.confirmPassword) 
                ? "border-red-500 focus:ring-red-500"
                : "focus:border-blue-500 focus:ring-blue-500"
            )}
            aria-invalid={touched.confirmPassword && !isFieldValid("confirmPassword", formData.confirmPassword)}
          />
          {touched.confirmPassword && !isFieldValid("confirmPassword", formData.confirmPassword) && (
            <p className="text-xs text-red-600 mt-1">
              Passwords do not match
            </p>
          )}
        </div>

        {/* Submit Button */}
        <Button 
          type="submit" 
          disabled={isLoading} 
          className="w-full group"
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
                Creating account...
              </>
            ) : (
              "Sign up"
            )}
          </motion.span>
        </Button>

        {/* Login Link */}
        <div className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-medium text-primary hover:text-primary/90 transition-colors duration-300"
          >
            Log in
          </Link>
        </div>
      </form>
    </div>
  );
};