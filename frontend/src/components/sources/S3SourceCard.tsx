// src/components/sources/S3SourceCard.tsx
import React from "react";
import { useS3Source } from "../../hooks/dataSource/useS3Source";

interface S3SourceCardProps {
  connectionId: string;
  config: any;
}

export const S3SourceCard: React.FC<S3SourceCardProps> = ({
  connectionId,
  config,
}) => {
  const { status, performOperation, disconnect } = useS3Source();

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">{config.bucket}</h3>
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
        <p>Region: {config.region}</p>
        <p>Bucket: {config.bucket}</p>
        {config.prefix && <p>Prefix: {config.prefix}</p>}
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={() => performOperation({ operation: "list", path: "/" })}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          List Objects
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
