import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu } from '@headlessui/react';
import { 
  LogOut, 
  User, 
  Settings, 
  HelpCircle 
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../../auth/hooks/useAuth';
import { Avatar, AvatarFallback, AvatarImage } from '@/common/components/ui/avatar';
import { cn } from '@/common/utils';

export const UserMenu: React.FC<{ user: any }> = ({ user }) => {
  const { logout } = useAuth();

  // Generate avatar fallback from user's name
  const getAvatarFallback = () => {
    if (!user) return '??';
    const initials = `${user.firstName?.[0] || ''}${user.lastName?.[0] || ''}`;
    return initials || '??';
  };

  const menuItems = [
    {
      label: 'Profile',
      icon: User,
      href: '/profile',
    },
    {
      label: 'Settings',
      icon: Settings,
      href: '/settings',
    },
    {
      label: 'Help',
      icon: HelpCircle,
      href: '/help',
    },
  ];

  return (
    <Menu as="div" className="relative">
      {({ open }) => (
        <>
          <Menu.Button 
            as={motion.button}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="flex items-center focus:outline-none"
          >
            <Avatar className="h-8 w-8 border-2 border-transparent hover:border-primary transition-all">
              <AvatarImage 
                src={user?.profileImage || '/default-avatar.png'} 
                alt={`${user?.firstName} ${user?.lastName}`} 
              />
              <AvatarFallback>{getAvatarFallback()}</AvatarFallback>
            </Avatar>
          </Menu.Button>

          <AnimatePresence>
            {open && (
              <Menu.Items
                static
                as={motion.div}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="absolute right-0 mt-2 w-64 bg-card border border-border rounded-lg shadow-lg z-50 overflow-hidden"
              >
                {/* User Info Header */}
                <div className="px-4 py-3 border-b border-border bg-muted/10">
                  <div className="flex items-center space-x-3">
                    <Avatar className="h-10 w-10">
                      <AvatarImage 
                        src={user?.profileImage || '/default-avatar.png'} 
                        alt={`${user?.firstName} ${user?.lastName}`} 
                      />
                      <AvatarFallback>{getAvatarFallback()}</AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {user?.firstName} {user?.lastName}
                      </p>
                      <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                        {user?.email}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="py-1">
                  {menuItems.map((item) => (
                    <Menu.Item key={item.href}>
                      {({ active }) => (
                        <Link
                          to={item.href}
                          className={cn(
                            "flex items-center px-4 py-2 text-sm transition-colors duration-200",
                            active 
                              ? "bg-accent text-accent-foreground" 
                              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                          )}
                        >
                          <item.icon className="mr-3 h-4 w-4" />
                          {item.label}
                        </Link>
                      )}
                    </Menu.Item>
                  ))}
                </div>

                {/* Logout */}
                <div className="border-t border-border py-1">
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={() => logout()}
                        className={cn(
                          "flex items-center w-full px-4 py-2 text-sm transition-colors duration-200",
                          active 
                            ? "bg-destructive/10 text-destructive" 
                            : "text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        )}
                      >
                        <LogOut className="mr-3 h-4 w-4" />
                        Sign out
                      </button>
                    )}
                  </Menu.Item>
                </div>
              </Menu.Items>
            )}
          </AnimatePresence>
        </>
      )}
    </Menu>
  );
};