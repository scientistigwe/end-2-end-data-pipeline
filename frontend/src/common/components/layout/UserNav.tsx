import React from "react";
import { User } from "@/common/types/user";

interface UserNavProps {
  user: User;
}

export const UserNav: React.FC<UserNavProps> = ({ user }) => {
  return (
    <div className="flex items-center space-x-2">
      <span className="text-sm text-foreground">{user.name}</span>
      <img
        src={user.avatarUrl}
        alt="User Avatar"
        className="h-8 w-8 rounded-full border border-border"
      />
    </div>
  );
};
