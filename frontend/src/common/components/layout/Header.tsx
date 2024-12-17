import React from "react";
import { Menu } from "lucide-react";
import { NotificationsPanel } from "./NotificationsPanel";
import { User } from "@/common/types/user";
import { useAppDispatch } from "@/store/store";
import { toggleSidebar } from "@/common/store/ui/uiSlice";
import PipelineLogo from "@/assets/PipelineLogo";

interface HeaderProps {
  user: User;
}

export const Header: React.FC<HeaderProps> = () => {
  const dispatch = useAppDispatch();

  return (
    <header className="bg-card border-b border-border h-16">
      <div className="h-full mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-full">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => dispatch(toggleSidebar())}
              className="p-2 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center space-x-2">
              <PipelineLogo className="h-8 w-8" />
              <span className="text-lg font-semibold text-foreground">
                Data Pipeline Manager
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <NotificationsPanel />
          </div>
        </div>
      </div>
    </header>
  );
};
