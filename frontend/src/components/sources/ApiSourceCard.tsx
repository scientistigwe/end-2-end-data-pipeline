// src/components/sources/ApiSourceCard.tsx
import React from "react";
import { useApiSource } from "../../hooks/dataSource/useApiSource";

interface ApiSourceCardProps {
  connectionId: string;
  config: any;
}

export const ApiSourceCard: React.FC<ApiSourceCardProps> = ({
  connectionId,
  config,
}) => {
  const { status, disconnect, fetchData } = useApiSource();

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">{config.url}</h3>
        <span
          className={`px-2 py-1 rounded-full text-sm ${
            status === "connected"
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {status}
        </span>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        <p>Method: {config.method}</p>
        <p>Last Fetch: {config.lastFetch || "Never"}</p>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={() => fetchData({})}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Fetch Data
        </button>
        <button
          onClick={() => disconnect()}
          className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Disconnect
        </button>
      </div>
    </div>
  );
};
