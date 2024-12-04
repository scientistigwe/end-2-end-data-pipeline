// components/errors/ServerError.tsx
import React from "react";
import { useNavigate } from "react-router-dom";

export const ServerError: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full px-6 py-8">
        <div className="text-center">
          <h1 className="text-9xl font-bold text-red-600">500</h1>
          <h2 className="mt-4 text-3xl font-semibold text-gray-700">
            Server Error
          </h2>
          <p className="mt-4 text-gray-600">
            Oops! Something went wrong on our end. Please try again later.
          </p>
          <div className="mt-8">
            <button
              onClick={() => window.location.reload()}
              className="mr-4 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Retry
            </button>
            <button
              onClick={() => navigate("/")}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Go Home
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
