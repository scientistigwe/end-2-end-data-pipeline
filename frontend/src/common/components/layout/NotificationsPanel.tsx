import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSelector } from "react-redux";
import { Bell, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import { selectNotifications } from "../../store/";
import { 
  Popover, 
  PopoverContent, 
  PopoverTrigger 
} from "@/common/components/ui/popover";
import { Button } from "@/common/components/ui/button";
import { cn } from "@/common/utils";

// Notification type mapping
const getNotificationIcon = (type: string) => {
  switch (type) {
    case 'success':
      return <CheckCircle2 className="text-green-500 w-5 h-5" />;
    case 'error':
      return <AlertCircle className="text-red-500 w-5 h-5" />;
    case 'warning':
      return <XCircle className="text-yellow-500 w-5 h-5" />;
    default:
      return <Bell className="text-blue-500 w-5 h-5" />;
  }
};

export const NotificationsPanel: React.FC = () => {
  const notifications = useSelector(selectNotifications);
  const [isOpen, setIsOpen] = useState(false);

  const unreadNotifications = notifications.filter(n => !n.read);

  const handleMarkAllAsRead = () => {
    // Dispatch action to mark all notifications as read
    // This would be implemented in your Redux store
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          className="relative p-2 rounded-full hover:bg-accent group"
        >
          <Bell className="w-5 h-5 text-muted-foreground group-hover:text-foreground" />
          
          <AnimatePresence>
            {unreadNotifications.length > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                className="absolute top-0 right-0 block h-3 w-3 rounded-full bg-destructive"
              >
                <span className="sr-only">
                  {unreadNotifications.length} unread notifications
                </span>
              </motion.span>
            )}
          </AnimatePresence>
        </motion.button>
      </PopoverTrigger>
      
      <PopoverContent 
        align="end" 
        className="w-96 max-h-[500px] overflow-y-auto"
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Notifications</h3>
          {unreadNotifications.length > 0 && (
            <Button 
              variant="ghost" 
              size="sm"
              onClick={handleMarkAllAsRead}
            >
              Mark all as read
            </Button>
          )}
        </div>

        <AnimatePresence>
          {notifications.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center py-6 text-muted-foreground"
            >
              No notifications
            </motion.div>
          ) : (
            <div className="space-y-2">
              {notifications.map((notification, index) => (
                <motion.div
                  key={notification.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.1 }}
                  className={cn(
                    "flex items-start space-x-3 p-3 rounded-lg",
                    notification.read 
                      ? "bg-muted/50" 
                      : "bg-primary/10 border border-primary/20"
                  )}
                >
                  {/* Notification Icon */}
                  <div className="mt-1">
                    {getNotificationIcon(notification.type)}
                  </div>

                  {/* Notification Content */}
                  <div className="flex-1">
                    <h4 className="text-sm font-medium">
                      {notification.title}
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {/* TODO: Format date */}
                      {notification.timestamp}
                    </p>
                  </div>

                  {/* Action Button */}
                  {notification.action && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Handle notification action
                        notification.action.handler();
                      }}
                    >
                      {notification.action.label}
                    </Button>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </AnimatePresence>
      </PopoverContent>
    </Popover>
  );
};