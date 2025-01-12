// src/auth/pages/ProfilePage.tsx
import React from "react";
import { motion } from "framer-motion";
import { Settings, KeyRound, User } from "lucide-react";
import { UserProfile } from "../components/UserProfile";
import { ChangePasswordModal } from "../components/ChangePasswordModal";
import { useModal } from "@/common/hooks/useModal";
import { Card, CardHeader, CardTitle, CardDescription } from "@/common/components/ui/card";
import { Button } from "@/common/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/common/components/ui/tabs";

const ProfilePage: React.FC = () => {
  const { open: openChangePassword } = useModal({ id: "change-password" });

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8"
    >
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="px-4 sm:px-0 flex items-center justify-between"
      >
        <div>
          <div className="flex items-center space-x-3">
            <Settings className="w-6 h-6 text-primary" />
            <h2 className="text-2xl font-bold text-foreground">Profile Settings</h2>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Manage your account settings and security preferences
          </p>
        </div>
      </motion.div>

      {/* Profile Content */}
      <Tabs defaultValue="profile" className="mt-6">
        <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto mb-6">
          <TabsTrigger value="profile" className="flex items-center space-x-2">
            <User className="w-4 h-4" />
            <span>Profile</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center space-x-2">
            <KeyRound className="w-4 h-4" />
            <span>Security</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <Card className="max-w-2xl mx-auto">
              <CardHeader>
                <CardTitle>Personal Information</CardTitle>
                <CardDescription>
                  Update your personal details and contact information
                </CardDescription>
              </CardHeader>
              <UserProfile onChangePassword={openChangePassword} />
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="security">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <Card className="max-w-2xl mx-auto">
              <CardHeader>
                <CardTitle>Account Security</CardTitle>
                <CardDescription>
                  Manage your account security settings
                </CardDescription>
              </CardHeader>
              <div className="p-6 space-y-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="text-lg font-medium">Change Password</h3>
                    <p className="text-sm text-muted-foreground">
                      Regularly updating your password helps keep your account secure
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={openChangePassword}
                  >
                    Change Password
                  </Button>
                </div>

                {/* Additional security options could be added here */}
                <div className="flex justify-between items-center border-t pt-4">
                  <div>
                    <h3 className="text-lg font-medium">Two-Factor Authentication</h3>
                    <p className="text-sm text-muted-foreground">
                      Add an extra layer of security to your account
                    </p>
                  </div>
                  <Button variant="outline">
                    Configure 2FA
                  </Button>
                </div>
              </div>
            </Card>
          </motion.div>
        </TabsContent>
      </Tabs>

      {/* Change Password Modal */}
      <ChangePasswordModal />
    </motion.div>
  );
};

export default ProfilePage;