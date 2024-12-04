// src/pages/SettingsPage.tsx
import React, { useState } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../store";

interface SettingsSection {
  id: string;
  title: string;
  description: string;
  component: React.FC;
}

// Profile Settings Component
const ProfileSettings: React.FC = () => {
  const user = useSelector((state: RootState) => state.auth.user);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium">Profile Settings</h2>
      {/* Profile settings form */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            type="email"
            defaultValue={user?.email}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
        {/* Add other profile fields as needed */}
      </div>
    </div>
  );
};

// Security Settings Component
const SecuritySettings: React.FC = () => {
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium">Security Settings</h2>
      <div className="space-y-4">
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md">
          Change Password
        </button>
        <div>
          <h3 className="text-sm font-medium text-gray-700">
            Two-Factor Authentication
          </h3>
          {/* Add 2FA settings */}
        </div>
      </div>
    </div>
  );
};

// Notification Settings Component
const NotificationSettings: React.FC = () => {
  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium">Notification Preferences</h2>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            Email Notifications
          </span>
          <input type="checkbox" className="rounded border-gray-300" />
        </div>
        {/* Add other notification preferences */}
      </div>
    </div>
  );
};

export const SettingsPage: React.FC = () => {
  const [activeSection, setActiveSection] = useState("profile");

  const sections: SettingsSection[] = [
    {
      id: "profile",
      title: "Profile",
      description: "Manage your profile information",
      component: ProfileSettings,
    },
    {
      id: "security",
      title: "Security",
      description: "Security and authentication settings",
      component: SecuritySettings,
    },
    {
      id: "notifications",
      title: "Notifications",
      description: "Configure notification preferences",
      component: NotificationSettings,
    },
  ];

  const ActiveComponent =
    sections.find((s) => s.id === activeSection)?.component || ProfileSettings;

  return (
    <div className="space-y-6">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="flex gap-6">
          {/* Settings Navigation */}
          <nav className="w-64 bg-white shadow rounded-lg p-4 h-fit">
            <ul className="space-y-1">
              {sections.map((section) => (
                <li key={section.id}>
                  <button
                    onClick={() => setActiveSection(section.id)}
                    className={`w-full text-left px-4 py-2 rounded-md ${
                      activeSection === section.id
                        ? "bg-blue-50 text-blue-700"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    <div>
                      <div>{section.title}</div>
                      <p className="text-sm text-gray-500">
                        {section.description}
                      </p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          {/* Settings Content */}
          <div className="flex-1 bg-white shadow rounded-lg p-6">
            <ActiveComponent />
          </div>
        </div>
      </main>
    </div>
  );
};
