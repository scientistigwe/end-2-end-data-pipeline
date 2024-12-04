// src/components/pipeline/PipelineCard.tsx
import React from 'react';
import { usePipeline } from '../../hooks/usePipeline';

interface PipelineCardProps {
  pipelineId: string;
}

export const PipelineCard: React.FC<PipelineCardProps> = ({ pipelineId }) => {
  const { status, progress, stopPipeline } = usePipeline({ pipelineId });

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">Pipeline {pipelineId}</h3>
        <span className={`px-2 py-1 rounded-full text-sm ${
          status === 'running' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
        }`}>
          {status}
        </span>
      </div>
      {progress !== undefined && (
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <span className="text-sm text-gray-600">{progress}%</span>
        </div>
      )}
      <button
        onClick={() => stopPipeline()}
        className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
      >
        Stop Pipeline
      </button>
    </div>
  );
};
AnalysisCard.tsx