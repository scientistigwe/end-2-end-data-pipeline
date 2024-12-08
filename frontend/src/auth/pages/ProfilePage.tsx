// src/auth/pages/ProfilePage.tsx
import React from "react";
import { UserProfile } from "../components/UserProfile";
import { ChangePasswordModal } from "../components/ChangePasswordModal";
import { useModal } from "@/common/hooks/useModal";
import { Card } from "@/common/components/ui/card";

export const ProfilePage: React.FC = () => {
  const { open: openChangePassword } = useModal({ id: "change-password" });

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 sm:px-0">
        <h2 className="text-2xl font-bold">Profile Settings</h2>
        <p className="mt-1 text-sm text-gray-600">
          Manage your account settings and security preferences.
        </p>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <UserProfile onChangePassword={openChangePassword} />
        </Card>
      </div>

      <ChangePasswordModal />
    </div>
  );
};

