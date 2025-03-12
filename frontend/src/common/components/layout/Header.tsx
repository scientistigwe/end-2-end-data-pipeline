import React from "react";
import { motion } from "framer-motion";
import { Menu, Search, Bell } from "lucide-react";
import { NotificationsPanel } from "./NotificationsPanel";
import { User } from "@/common/types/user";
import { useAppDispatch } from "@/store/store";
import { toggleSidebar } from "@/common/store/ui/uiSlice";
import PipelineLogo from "@/assets/PipelineLogo";
import { Input } from "@/common/components/ui/inputs";
import { Button } from "@/common/components/ui/button";
import { UserNav } from "./UserNav";

interface HeaderProps {
  user: User;
}

export const Header: React.FC<HeaderProps> = ({ user }) => {
  const dispatch = useAppDispatch();

  return (
    <motion.header
      initial={{ opacity: 0, y: -50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="sticky top-0 z-50 bg-card border-b border-border h-16"
    >
      <div className="h-full mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-full">
          {/* Left Side: Menu & Logo */}
          <div className="flex items-center space-x-4">
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => dispatch(toggleSidebar())}
              className="p-2 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
              aria-label="Toggle Sidebar"
            >
              <Menu className="h-5 w-5" />
            </motion.button>

            <div className="flex items-center space-x-2">
              <PipelineLogo className="h-8 w-8 transition-transform hover:rotate-6" />
              <span className="text-lg font-semibold text-foreground">
                Analytix Flow
              </span>
            </div>
          </div>

          {/* Center: Search Bar */}
          <div className="flex-1 max-w-xl mx-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search pipelines, projects..."
                className="pl-10 w-full"
              />
            </div>
          </div>

          {/* Right Side: Notifications & User Menu */}
          <div className="flex items-center space-x-4">
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              className="relative text-muted-foreground hover:text-foreground"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              <span className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground text-xs rounded-full h-4 w-4 flex items-center justify-center">
                3
              </span>
            </motion.button>

            <UserNav user={user} />
          </div>
        </div>
      </div>
    </motion.header>
  );
};
