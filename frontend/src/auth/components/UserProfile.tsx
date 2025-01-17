// src/auth/components/UserProfile.tsx
import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Edit2,
  Save,
  X,
  Key,
  AlertCircle,
  CheckCircle2,
  Camera,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components//ui/inputs/input";
import { Alert } from "@/common/components/ui/alert";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/common/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/common/components/ui/dialog";
import type { User } from "@/common";
import { cn } from "@/common/utils";

interface UserProfileProps {
  onChangePassword: () => void;
}

export const UserProfile: React.FC<UserProfileProps> = ({
  onChangePassword,
}) => {
  const { user, updateProfile, uploadProfileImage } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<User>>({
    firstName: user?.firstName || "",
    lastName: user?.lastName || "",
    email: user?.email || "",
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isImageUploadDialogOpen, setIsImageUploadDialogOpen] = useState(false);

  // Validation rules
  const validationRules = useMemo(
    () => ({
      firstName: (value: string) => value.trim().length >= 2,
      lastName: (value: string) => value.trim().length >= 2,
      email: (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
    }),
    []
  );

  // Check if a field is valid
  const isFieldValid = (name: string, value: string) => {
    return validationRules[name] ? validationRules[name](value) : true;
  };

  // Handle profile image upload
  const handleImageUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        await uploadProfileImage(file);
        setIsImageUploadDialogOpen(false);
      } catch (err: any) {
        setError(err.message || "Failed to upload profile image");
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    // Validate all fields before submission
    const isValid = Object.keys(validationRules).every((key) =>
      isFieldValid(key, formData[key] || "")
    );

    if (!isValid) {
      setError("Please correct the form errors");
      setIsLoading(false);
      return;
    }

    try {
      await updateProfile(formData);
      setIsEditing(false);
    } catch (err: any) {
      setError(err.message || "Failed to update profile");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear any previous errors
    if (error) setError(null);
  };

  const cancelEditing = () => {
    // Reset form data to original values
    setFormData({
      firstName: user?.firstName || "",
      lastName: user?.lastName || "",
      email: user?.email || "",
    });
    setIsEditing(false);
    setError(null);
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white dark:bg-gray-900 rounded-lg shadow-md">
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

      {/* Profile Header */}
      <div className="flex items-center space-x-6 mb-8">
        {/* Avatar with Upload Option */}
        <div className="relative">
          <Avatar className="h-24 w-24 border-4 border-primary/10">
            <AvatarImage
              src={user?.profileImage}
              alt={`${user?.firstName} ${user?.lastName}'s profile`}
            />
            <AvatarFallback className="text-3xl">
              {user?.firstName?.[0]}
              {user?.lastName?.[0]}
            </AvatarFallback>
          </Avatar>

          {/* Camera Icon for Image Upload */}
          <button
            onClick={() => setIsImageUploadDialogOpen(true)}
            className="absolute bottom-0 right-0 bg-primary text-white rounded-full p-2 shadow-lg hover:bg-primary/90 transition-colors"
            aria-label="Upload profile image"
          >
            <Camera className="w-5 h-5" />
          </button>
        </div>

        {/* User Info */}
        <div>
          <h2 className="text-2xl font-bold text-foreground">
            {user?.firstName} {user?.lastName}
          </h2>
          <p className="text-muted-foreground">{user?.email}</p>
        </div>
      </div>

      {/* Profile Edit Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid md:grid-cols-2 gap-4">
          {/* First Name */}
          <div className="space-y-2">
            <label
              htmlFor="firstName"
              className="block text-sm font-medium text-foreground flex justify-between items-center"
            >
              First Name
              {formData.firstName &&
                (isFieldValid("firstName", formData.firstName) ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-500" />
                ))}
            </label>
            <Input
              id="firstName"
              name="firstName"
              type="text"
              value={formData.firstName || ""}
              onChange={handleChange}
              disabled={!isEditing || isLoading}
              className={cn(
                "w-full",
                isEditing &&
                  formData.firstName &&
                  !isFieldValid("firstName", formData.firstName)
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
            />
            {isEditing &&
              formData.firstName &&
              !isFieldValid("firstName", formData.firstName) && (
                <p className="text-xs text-red-600 mt-1">
                  First name must be at least 2 characters
                </p>
              )}
          </div>

          {/* Last Name */}
          <div className="space-y-2">
            <label
              htmlFor="lastName"
              className="block text-sm font-medium text-foreground flex justify-between items-center"
            >
              Last Name
              {formData.lastName &&
                (isFieldValid("lastName", formData.lastName) ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-500" />
                ))}
            </label>
            <Input
              id="lastName"
              name="lastName"
              type="text"
              value={formData.lastName || ""}
              onChange={handleChange}
              disabled={!isEditing || isLoading}
              className={cn(
                "w-full",
                isEditing &&
                  formData.lastName &&
                  !isFieldValid("lastName", formData.lastName)
                  ? "border-red-500 focus:ring-red-500"
                  : "focus:border-blue-500 focus:ring-blue-500"
              )}
            />
            {isEditing &&
              formData.lastName &&
              !isFieldValid("lastName", formData.lastName) && (
                <p className="text-xs text-red-600 mt-1">
                  Last name must be at least 2 characters
                </p>
              )}
          </div>
        </div>

        {/* Email */}
        <div className="space-y-2">
          <label
            htmlFor="email"
            className="block text-sm font-medium text-foreground flex justify-between items-center"
          >
            Email
            {formData.email &&
              (isFieldValid("email", formData.email) ? (
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-500" />
              ))}
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email || ""}
            onChange={handleChange}
            disabled={!isEditing || isLoading}
            className={cn(
              "w-full",
              isEditing &&
                formData.email &&
                !isFieldValid("email", formData.email)
                ? "border-red-500 focus:ring-red-500"
                : "focus:border-blue-500 focus:ring-blue-500"
            )}
          />
          {isEditing &&
            formData.email &&
            !isFieldValid("email", formData.email) && (
              <p className="text-xs text-red-600 mt-1">
                Please enter a valid email address
              </p>
            )}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-4">
          {isEditing ? (
            <div className="flex space-x-4">
              <Button
                type="button"
                variant="outline"
                onClick={cancelEditing}
                disabled={isLoading}
                className="flex items-center space-x-2"
              >
                <X className="w-4 h-4" />
                <span>Cancel</span>
              </Button>
              <Button
                type="submit"
                disabled={isLoading}
                className="flex items-center space-x-2"
              >
                {isLoading ? (
                  <span className="animate-spin">⭯</span>
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>{isLoading ? "Saving..." : "Save Changes"}</span>
              </Button>
            </div>
          ) : (
            <div className="flex space-x-4">
              <Button
                type="button"
                onClick={() => setIsEditing(true)}
                variant="outline"
                className="flex items-center space-x-2"
              >
                <Edit2 className="w-4 h-4" />
                <span>Edit Profile</span>
              </Button>
              <Button
                type="button"
                onClick={onChangePassword}
                variant="secondary"
                className="flex items-center space-x-2"
              >
                <Key className="w-4 h-4" />
                <span>Change Password</span>
              </Button>
            </div>
          )}
        </div>
      </form>

      {/* Profile Image Upload Dialog */}
      <Dialog
        open={isImageUploadDialogOpen}
        onOpenChange={setIsImageUploadDialogOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Profile Picture</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <input
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="block w-full text-sm text-slate-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-primary/10 file:text-primary
                hover:file:bg-primary/20"
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
