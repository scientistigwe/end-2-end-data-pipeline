// src/components/sources/StreamSourceCard.tsx
import React from "react";
import { useStreamSource } from "../../hooks/dataSource/useStreamSource";

interface StreamSourceCardProps {
  connectionId: string;
  config: any;
}

export const StreamSourceCard: React.FC<StreamSourceCardProps> = ({
  connectionId,
  config,
}) => {
  const { status, messages, pauseStream, resumeStream, disconnect } =
    useStreamSource();

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">{config.type} Stream</h3>
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
        {config.topic && <p>Topic: {config.topic}</p>}
        {config.queue && <p>Queue: {config.queue}</p>}
        <p>Messages Received: {messages.length}</p>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={() => (status === "paused" ? resumeStream() : pauseStream())}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {status === "paused" ? "Resume" : "Pause"}
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
