import React from "react";
import { UserMenu } from "./UserMenu";
import { NotificationsPanel } from "./NotificationsPanel";
import { User } from "@/common/types/user";

interface HeaderProps {
  user: User;
}

export const Header: React.FC<HeaderProps> = ({ user }) => {
  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">{/* Logo/Brand */}</div>
          <div className="flex items-center space-x-4">
            <NotificationsPanel />
            <UserMenu user={user} />
          </div>
        </div>
      </div>
    </header>
  );
};