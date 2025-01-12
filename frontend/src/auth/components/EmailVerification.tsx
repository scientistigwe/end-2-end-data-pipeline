// src/auth/components/EmailVerification.tsx
import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CheckCircle2,
  AlertCircle,
  RefreshCcw
} from 'lucide-react';
import { Alert, AlertTitle, AlertDescription } from '@/common/components/ui/alert';
import { Button } from '@/common/components/ui/button';
import { useAuth } from '../hooks/useAuth';

export const EmailVerification: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { verifyEmail, resendVerificationEmail } = useAuth();
  const [isVerifying, setIsVerifying] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }

    const verify = async () => {
      try {
        await verifyEmail({ token });
        // Wait briefly to show success message
        setTimeout(() => navigate('/login'), 3000);
      } catch (err: any) {
        setError(err.message || 'Verification failed');
      } finally {
        setIsVerifying(false);
      }
    };

    verify();
  }, [token, verifyEmail, navigate]);

  const handleResendVerification = async () => {
    setIsResending(true);
    setError(null);

    try {
      // Assuming resendVerificationEmail accepts email or token
      await resendVerificationEmail({ token });
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to resend verification email');
    } finally {
      setIsResending(false);
    }
  };

  // Verification in progress
  if (isVerifying) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center space-y-6 max-w-md mx-auto"
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{
            repeat: Infinity,
            duration: 1,
            ease: "linear"
          }}
          className="mx-auto w-16 h-16 border-4 border-primary/30 border-t-primary rounded-full"
        />
        <div>
          <h2 className="text-xl font-semibold text-foreground mb-2">
            Verifying Your Email
          </h2>
          <p className="text-muted-foreground">
            Please wait while we verify your email address
          </p>
        </div>
      </motion.div>
    );
  }

  // Verification failed
  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-6 max-w-md mx-auto"
      >
        <Alert variant="destructive">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle>Verification Failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>

        <div className="space-y-4">
          <Button
            onClick={handleResendVerification}
            disabled={isResending}
            className="w-full"
          >
            {isResending ? (
              <div className="flex items-center">
                <RefreshCcw className="mr-2 h-4 w-4 animate-spin" />
                Resending Verification
              </div>
            ) : (
              "Resend Verification Email"
            )}
          </Button>

          <Button
            variant="outline"
            className="w-full"
            onClick={() => navigate('/login')}
          >
            Return to Login
          </Button>
        </div>
      </motion.div>
    );
  }

  // Successful Verification
  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6 max-w-md mx-auto"
    >
      <Alert variant="success">
        <CheckCircle2 className="h-5 w-5" />
        <AlertTitle>Email Verified Successfully!</AlertTitle>
        <AlertDescription>
          You will be redirected to login momentarily...
        </AlertDescription>
      </Alert>

      <Button
        className="w-full"
        onClick={() => navigate('/login')}
      >
        Proceed to Login
      </Button>
    </motion.div>
  );
};