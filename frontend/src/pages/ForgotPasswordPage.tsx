// pages/auth/ForgotPasswordPage.tsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export const ForgotPasswordPage: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      // Add your password reset logic here
      // For example: await api.sendPasswordResetEmail(email);
      setIsSubmitted(true);
    } catch (err) {
      setError("Failed to send reset email. Please try again.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full px-6 py-8 bg-white shadow-md rounded-lg">
        {!isSubmitted ? (
          <>
            <div className="text-center">
              <h2 className="text-3xl font-bold text-gray-900">
                Forgot Password
              </h2>
              <p className="mt-2 text-gray-600">
                Enter your email address and we'll send you a link to reset your
                password.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="mt-8 space-y-6">
              {error && (
                <div className="p-3 text-red-500 bg-red-50 rounded-md">
                  {error}
                </div>
              )}

              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-gray-700"
                >
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md 
                           shadow-sm focus:outline-none focus:ring-blue-500 
                           focus:border-blue-500"
                  placeholder="Enter your email"
                />
              </div>

              <div>
                <button
                  type="submit"
                  className="w-full py-2 px-4 border border-transparent rounded-md 
                           shadow-sm text-white bg-blue-600 hover:bg-blue-700 
                           focus:outline-none focus:ring-2 focus:ring-offset-2 
                           focus:ring-blue-500"
                >
                  Send Reset Link
                </button>
              </div>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => navigate("/login")}
                  className="text-sm text-blue-600 hover:text-blue-500"
                >
                  Back to Login
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-900">
              Check Your Email
            </h2>
            <p className="mt-2 text-gray-600">
              If an account exists with {email}, we've sent password reset
              instructions.
            </p>
            <button
              onClick={() => navigate("/login")}
              className="mt-6 text-blue-600 hover:text-blue-500"
            >
              Return to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
