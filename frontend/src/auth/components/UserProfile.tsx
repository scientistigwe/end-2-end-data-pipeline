// src/auth/components/UserProfile.tsx
import React, { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components//ui/inputs/input";
import { Alert } from "@/common/components/ui/alert";
import { Avatar } from "@/common/components/ui/avatar";
import type { User } from "../types/auth";

interface UserProfileProps {
  onChangePassword: () => void;
}

export const UserProfile: React.FC<UserProfileProps> = ({
  onChangePassword,
}) => {
  const { user, updateProfile } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<User>>({
    firstName: user?.firstName,
    lastName: user?.lastName,
    email: user?.email,
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

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
  };

  return (
    <div className="p-6">
      {error && (
        <Alert variant="destructive" className="mb-4">
          <p>{error}</p>
        </Alert>
      )}

      <div className="flex items-center space-x-4 mb-6">
        <Avatar
          src={user?.profileImage}
          fallback={`${user?.firstName?.[0]}${user?.lastName?.[0]}`}
          className="h-16 w-16"
        />
        <div>
          <h3 className="text-lg font-medium">
            {user?.firstName} {user?.lastName}
          </h3>
          <p className="text-sm text-gray-500">{user?.email}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="firstName"
              className="block text-sm font-medium text-gray-700"
            >
              First Name
            </label>
            <Input
              id="firstName"
              name="firstName"
              type="text"
              value={formData.firstName || ""}
              onChange={handleChange}
              disabled={!isEditing || isLoading}
              className="mt-1"
            />
          </div>

          <div>
            <label
              htmlFor="lastName"
              className="block text-sm font-medium text-gray-700"
            >
              Last Name
            </label>
            <Input
              id="lastName"
              name="lastName"
              type="text"
              value={formData.lastName || ""}
              onChange={handleChange}
              disabled={!isEditing || isLoading}
              className="mt-1"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700"
          >
            Email
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email || ""}
            onChange={handleChange}
            disabled={!isEditing || isLoading}
            className="mt-1"
          />
        </div>

        <div className="flex justify-between pt-4">
          {isEditing ? (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditing(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? "Saving..." : "Save Changes"}
              </Button>
            </>
          ) : (
            <>
              <Button
                type="button"
                onClick={() => setIsEditing(true)}
                variant="outline"
              >
                Edit Profile
              </Button>
              <Button type="button" onClick={onChangePassword}>
                Change Password
              </Button>
            </>
          )}
        </div>
      </form>
    </div>
  );
};
