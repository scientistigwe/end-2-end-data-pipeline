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

export const RegisterForm: React.FC<RegisterFormProps> = ({
  onSubmit,
  isLoading = false,
}) => {
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<RegisterData>({
    email: "",
    password: "",
    confirm_password: "",
    username: "",
    first_name: "",
    last_name: "",
    terms_accepted: false,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    locale: navigator.language
  });

  const [touched, setTouched] = useState<{
    [key: string]: boolean;
  }>({});
  const [showPassword, setShowPassword] = useState(false);

  // Validation rules
  const validationRules = useMemo(() => ({
    first_name: (value: string) => value.trim().length >= 2,
    last_name: (value: string) => value.trim().length >= 2,
    username: (value: string) => /^[a-zA-Z0-9_]{3,16}$/.test(value),
    email: (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
    password: (value: string) => {
      const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
      return passwordRegex.test(value);
    },
    confirm_password: (value: string) => value === formData.password,
    terms_accepted: (value: boolean) => value === true
  }), [formData.password]);

  // Handle input changes
  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
    
    setTouched(prev => ({ ...prev, [name]: true }));
    if (error) setError(null);
  }, [error]);

  // Validate entire form
  const validateForm = useCallback((): boolean => {
    const isValid = Object.keys(validationRules).every(key => 
      isFieldValid(key, formData[key])
    );

    if (!isValid) {
      setError("Please correct the errors in the form");
      return false;
    }

    return true;
  }, [formData, validationRules]);

  // Validate individual field
  const isFieldValid = (name: string, value: any) => {
    return validationRules[name] ? validationRules[name](value) : true;
  };

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

    try {
      await onSubmit(formData);
    } catch (err) {
      if (isAuthError(err)) {
        setError(getErrorMessage(err));
      } else {
        setError("Registration failed. Please try again.");
      }
    }
  };

  const renderValidationIcon = (fieldName: string, value: any) => {
    if (!touched[fieldName]) return null;

    const isValid = isFieldValid(fieldName, value);
    return isValid ? (
      <CheckCircle2 className="w-5 h-5 text-green-500" />
    ) : (
      <XCircle className="w-5 h-5 text-red-500" />
    );
  };

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

        {/* Name Fields */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label htmlFor="first_name" className="text-sm font-medium text-foreground flex justify-between items-center">
              First Name
              {renderValidationIcon("first_name", formData.first_name)}
            </label>
            <Input
              id="first_name"
              name="first_name"
              type="text"
              required
              value={formData.first_name}
              onChange={handleChange}
              className={cn(
                "w-full",
                touched.first_name && !isFieldValid("first_name", formData.first_name) 
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="last_name" className="text-sm font-medium text-foreground flex justify-between items-center">
              Last Name
              {renderValidationIcon("last_name", formData.last_name)}
            </label>
            <Input
              id="last_name"
              name="last_name"
              type="text"
              required
              value={formData.last_name}
              onChange={handleChange}
              className={cn(
                "w-full",
                touched.last_name && !isFieldValid("last_name", formData.last_name) 
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
            />
          </div>
        </div>

        {/* Email Field */}
        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium text-foreground flex justify-between items-center">
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
            className={cn(
              "w-full",
              touched.email && !isFieldValid("email", formData.email) 
                ? "border-red-500 focus:ring-red-500"
                : "focus:border-blue-500 focus:ring-blue-500"
            )}
          />
        </div>

        {/* Username Field */}
        <div className="space-y-2">
          <label htmlFor="username" className="text-sm font-medium text-foreground flex justify-between items-center">
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
            className={cn(
              "w-full",
              touched.username && !isFieldValid("username", formData.username) 
                ? "border-red-500 focus:ring-red-500"
                : "focus:border-blue-500 focus:ring-blue-500"
            )}
          />
        </div>

        {/* Password Fields */}
        <div className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium text-foreground flex justify-between items-center">
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
                className={cn(
                  "w-full pr-10",
                  touched.password && !isFieldValid("password", formData.password) 
                    ? "border-red-500 focus:ring-red-500"
                    : "focus:border-blue-500 focus:ring-blue-500"
                )}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
            {passwordStrength && (
              <div className="flex items-center mt-2 space-x-2">
                <div className={cn(
                  "h-2 flex-1 rounded",
                  passwordStrength === "Weak" ? "bg-red-500" :
                  passwordStrength === "Moderate" ? "bg-yellow-500" :
                  "bg-green-500"
                )} />
                <span className="text-sm text-gray-600">{passwordStrength}</span>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="confirm_password" className="text-sm font-medium text-foreground flex justify-between items-center">
              Confirm Password
              {renderValidationIcon("confirm_password", formData.confirm_password)}
            </label>
            <Input
              id="confirm_password"
              name="confirm_password"
              type="password"
              required
              value={formData.confirm_password}
              onChange={handleChange}
              className={cn(
                "w-full",
                touched.confirm_password && !isFieldValid("confirm_password", formData.confirm_password) 
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
            />
          </div>
        </div>

        {/* Terms Acceptance */}
        <div className="flex items-center space-x-2">
          <input
            id="terms_accepted"
            name="terms_accepted"
            type="checkbox"
            checked={formData.terms_accepted}
            onChange={handleChange}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="terms_accepted" className="text-sm text-gray-600">
            I accept the terms and conditions
          </label>
        </div>

        {/* Submit Button */}
        <Button 
          type="submit"
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? "Creating account..." : "Register"}
        </Button>

        {/* Login Link */}
        <p className="text-center text-sm text-gray-600">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-600 hover:text-blue-800">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
};