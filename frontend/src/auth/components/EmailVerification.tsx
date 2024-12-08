// src/auth/components/EmailVerification.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Alert } from '@/common/components/ui/alert';
import { Button } from '@/common/components/ui/button';
import { useAuth } from '../hooks/useAuth';

export const EmailVerification: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { verifyEmail } = useAuth();
  const [isVerifying, setIsVerifying] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

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

  if (isVerifying) {
    return (
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"/>
        <p className="mt-4 text-gray-600">Verifying your email...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Alert variant="destructive">
          <p>{error}</p>
        </Alert>
        <Button
          variant="outline"
          className="w-full"
          onClick={() => navigate('/login')}
        >
          Return to login
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Alert variant="success">
        <h3 className="font-medium">Email verified successfully!</h3>
        <p>You will be redirected to login shortly...</p>
      </Alert>
    </div>
  );
};