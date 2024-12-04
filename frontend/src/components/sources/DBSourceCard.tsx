// src/components/sources/DBSourceCard.tsx
import React from "react";
import { useDBSource } from "../../hooks/dataSource/useDBSource";

interface DBSourceCardProps {
  connectionId: string;
  config: any;
}

export const DBSourceCard: React.FC<DBSourceCardProps> = ({
  connectionId,
  config,
}) => {
  const { status, executeQuery, disconnect } = useDBSource();

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">
          {config.database}@{config.host}
        </h3>
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
        <p>Type: {config.type}</p>
        <p>Database: {config.database}</p>
      </div>

      <div className="mt-4">
        <textarea
          className="w-full p-2 border rounded"
          placeholder="Enter SQL query..."
        />
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => executeQuery({ query: "SELECT 1" })}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Execute Query
          </button>
          <button
            onClick={() => disconnect()}
            className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Disconnect
          </button>
        </div>
      </div>
    </div>
  );
};
