// src/components/layout/UserMenu.tsx
import { Menu } from '@headlessui/react';
import { useAuth } from '../../hooks/useAuth';

export const UserMenu: React.FC<{ user: any }> = ({ user }) => {
  const { logout } = useAuth();

  return (
    <Menu as="div" className="relative">
      <Menu.Button className="flex items-center">
        <img
          className="h-8 w-8 rounded-full"
          src={user.avatar || '/default-avatar.png'}
          alt=""
        />
      </Menu.Button>

      <Menu.Items className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg">
        <Menu.Item>
          {({ active }) => (
            <button
              className={`${
                active ? 'bg-gray-100' : ''
              } block px-4 py-2 text-sm text-gray-700 w-full text-left`}
              onClick={() => logout()}
            >
              Sign out
            </button>
          )}
        </Menu.Item>
      </Menu.Items>
    </Menu>
  );
};
