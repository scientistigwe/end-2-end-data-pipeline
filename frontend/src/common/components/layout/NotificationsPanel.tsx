// src/components/layout/NotificationsPanel.tsx
import { useSelector } from "react-redux";
import { selectNotifications } from "../../store/";

export const NotificationsPanel: React.FC = () => {
  const notifications = useSelector(selectNotifications);

  return (
    <div className="relative">
      <button className="relative p-1 rounded-full hover:bg-gray-100">
        <span className="sr-only">View notifications</span>
        {/* Bell icon */}
        {notifications.length > 0 && (
          <span className="absolute top-0 right-0 block h-2 w-2 rounded-full bg-red-400" />
        )}
      </button>
    </div>
  );
};
