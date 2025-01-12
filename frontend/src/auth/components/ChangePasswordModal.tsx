// src/auth/components/ChangePasswordModal.tsx
import React, { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/common/components/ui/overlays/dialog";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/inputs/input";
import { Alert } from "@/common/components/ui/alert";
import { useModal } from "@/common/hooks/useModal";
import { useAuth } from "../hooks/useAuth";
import type { ChangePasswordData } from "../types/auth";
import { useSelector } from "react-redux";
import { selectActiveModals } from "@/common/store/ui/selectors";
import type { Modal } from "@/common/types/ui";
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  Eye,
  EyeOff
} from "lucide-react";
import { cn } from "@/lib/utils";

export const ChangePasswordModal: React.FC = () => {
  const MODAL_ID = "change-password";
  const { close } = useModal({ id: MODAL_ID });

  // Get modal state from store
  const activeModals = useSelector(selectActiveModals);
  const isOpen = activeModals.some((modal: Modal) => modal.id === MODAL_ID);

  const { changePassword } = useAuth();
  const [formData, setFormData] = useState<ChangePasswordData>({
    currentPassword: "",
    newPassword: "",
  });
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [touched, setTouched] = useState<{ [key: string]: boolean }>({});
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });

  // Validation rules
  const validationRules = useMemo(() => ({
    currentPassword: (value: string) => value.length >= 6,
    newPassword: (value: string) => {
      // At least 8 characters, one uppercase, one lowercase, one number, one special char
      const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
      return passwordRegex.test(value);
    },
    confirmPassword: (value: string) => value === formData.newPassword
  }), [formData.newPassword]);

  // Check if a field is valid
  const isFieldValid = useCallback((name: string, value: string) => {
    return validationRules[name] ? validationRules[name](value) : true;
  }, [validationRules]);

  // Get password strength
  const getPasswordStrength = useCallback((password: string) => {
    if (password.length === 0) return null;
    if (password.length < 8) return "Weak";
    if (!validationRules.newPassword(password)) return "Moderate";
    return "Strong";
  }, [validationRules]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Mark all fields as touched
    setTouched({
      currentPassword: true,
      newPassword: true,
      confirmPassword: true
    });

    // Validate all fields
    const isValid = Object.keys(validationRules).every(key =>
      isFieldValid(key, key === 'confirmPassword' ? confirmPassword : formData[key])
    );

    if (!isValid) {
      setError("Please correct the errors in the form");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await changePassword(formData);
      close();
      // Reset form
      setFormData({ currentPassword: "", newPassword: "" });
      setConfirmPassword("");
      setTouched({});
    } catch (err: any) {
      setError(err.message || "Failed to change password");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;

    // Update form data
    if (name === "confirmPassword") {
      setConfirmPassword(value);
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }

    // Mark field as touched
    setTouched((prev) => ({ ...prev, [name]: true }));

    // Clear any previous errors
    if (error) setError(null);
  };

  // Toggle password visibility
  const togglePasswordVisibility = (field: 'current' | 'new' | 'confirm') => {
    setShowPasswords(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  // Render validation icon
  const renderValidationIcon = (fieldName: string, value: string) => {
    if (!touched[fieldName]) return null;

    const isValid = fieldName === 'confirmPassword'
      ? isFieldValid(fieldName, value)
      : isFieldValid(fieldName, value);

    return isValid ? (
      <CheckCircle2 className="w-5 h-5 text-green-500" />
    ) : (
      <XCircle className="w-5 h-5 text-red-500" />
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change Password</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Alert */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="mb-4"
              >
                <Alert variant="destructive">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="w-5 h-5" />
                    <p>{error}</p>
                  </div>
                </Alert>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Current Password */}
          <div className="space-y-2">
            <label
              htmlFor="currentPassword"
              className="block text-sm font-medium text-foreground flex justify-between items-center"
            >
              Current Password
              {renderValidationIcon("currentPassword", formData.currentPassword)}
            </label>
            <div className="relative">
              <Input
                id="currentPassword"
                name="currentPassword"
                type={showPasswords.current ? "text" : "password"}
                value={formData.currentPassword}
                onChange={handleChange}
                disabled={isLoading}
                className={cn(
                  "w-full pr-10",
                  touched.currentPassword &&
                  !isFieldValid('currentPassword', formData.currentPassword)
                    ? "border-red-500 focus:ring-red-500"
                    : "focus:border-blue-500 focus:ring-blue-500"
                )}
                required
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => togglePasswordVisibility('current')}
                aria-label={showPasswords.current ? "Hide password" : "Show password"}
              >
                {showPasswords.current ? (
                  <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                )}
              </button>
            </div>
            {touched.currentPassword &&
              !isFieldValid('currentPassword', formData.currentPassword) && (
                <p className="text-xs text-red-600 mt-1">
                  Current password must be at least 6 characters
                </p>
            )}
          </div>

          {/* New Password */}
          <div className="space-y-2">
            <label
              htmlFor="newPassword"
              className="block text-sm font-medium text-foreground flex justify-between items-center"
            >
              New Password
              {renderValidationIcon("newPassword", formData.newPassword)}
            </label>
            <div className="relative">
              <Input
                id="newPassword"
                name="newPassword"
                type={showPasswords.new ? "text" : "password"}
                value={formData.newPassword}
                onChange={handleChange}
                disabled={isLoading}
                className={cn(
                  "w-full pr-10",
                  touched.newPassword &&
                  !isFieldValid('newPassword', formData.newPassword)
                    ? "border-red-500 focus:ring-red-500"
                    : "focus:border-blue-500 focus:ring-blue-500"
                )}
                required
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => togglePasswordVisibility('new')}
                aria-label={showPasswords.new ? "Hide password" : "Show password"}
              >
                {showPasswords.new ? (
                  <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                )}
              </button>
            </div>
            {touched.newPassword && (
              <>
                {!isFieldValid('newPassword', formData.newPassword) && (
                  <p className="text-xs text-red-600 mt-1">
                    Password must be 8+ characters, include uppercase, lowercase, number, and special character
                  </p>
                )}
                {formData.newPassword && (
                  <div className="mt-1 flex items-center space-x-2">
                    <div
                      className={cn(
                        "h-1.5 w-1/3 rounded-full",
                        getPasswordStrength(formData.newPassword) === "Weak" && "bg-red-500",
                        getPasswordStrength(formData.newPassword) === "Moderate" && "bg-yellow-500",
                        getPasswordStrength(formData.newPassword) === "Strong" && "bg-green-500"
                      )}
                    />
                    <p className="text-xs text-gray-500">
                      {getPasswordStrength(formData.newPassword)} password
                    </p>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Confirm New Password */}
          <div className="space-y-2">
            <label
              htmlFor="confirmPassword"
              className="block text-sm font-medium text-foreground flex justify-between items-center"
            >
              Confirm New Password
              {renderValidationIcon("confirmPassword", confirmPassword)}
            </label>
            <div className="relative">
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type={showPasswords.confirm ? "text" : "password"}
                value={confirmPassword}
                onChange={handleChange}
                disabled={isLoading}
                className={cn(
                  "w-full pr-10",
                  touched.confirmPassword &&
                  !isFieldValid('confirmPassword', confirmPassword)
                    ? "border-red-500 focus:ring-red-500"
                    : "focus:border-blue-500 focus:ring-blue-500"
                )}
                required
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => togglePasswordVisibility('confirm')}
                aria-label={showPasswords.confirm ? "Hide password" : "Show password"}
              >
                {showPasswords.confirm ? (
                  <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                )}
              </button>
            </div>
            {touched.confirmPassword &&
              !isFieldValid('confirmPassword', confirmPassword) && (
                <p className="text-xs text-red-600 mt-1">
                  Passwords do not match
                </p>
            )}
          </div>

          <DialogFooter className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={close}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
              className="group"
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
                    Changing Password...
                  </>
                ) : (
                  "Change Password"
                )}
              </motion.span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};