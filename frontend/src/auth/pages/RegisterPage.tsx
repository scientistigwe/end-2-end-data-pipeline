// src/auth/pages/RegisterPage.tsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { RegisterForm } from '../components/RegisterForm';
import { AuthLayout } from '../components/AuthLayout';
import { useAuth } from '../hooks/useAuth';
import type { RegisterData } from '../types/auth';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const handleRegister = async (data: RegisterData) => {
    try {
      await register(data);
      navigate('/login', { 
        replace: true,
        state: { message: 'Registration successful! Please log in.' }
      });
    } catch (error) {
      throw error;
    }
  };

  return (
    <AuthLayout>
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Create your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Already have an account?{' '}
          <a href="/login" className="font-medium text-blue-600 hover:text-blue-500">
            Sign in
          </a>
        </p>
      </div>
      <RegisterForm onSubmit={handleRegister} />
    </AuthLayout>
  );
};

export default RegisterPage