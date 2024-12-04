// src/components/analysis/AnalysisCard.tsx
import React from 'react';
import { useAnalysis } from '../../hooks/analysis/useAnalysis';

interface AnalysisCardProps {
  analysisId: string;
  type: 'quality' | 'insight';
}

export const AnalysisCard: React.FC<AnalysisCardProps> = ({ analysisId, type }) => {
  const { status, report, refreshReport } = useAnalysis({
    analysisId,
    analysisType: type
  });

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">{type} Analysis</h3>
        <button
          onClick={() => refreshReport()}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>
      {report && (
        <div className="mt-4">
          {/* Render analysis results */}
        </div>
      )}
    </div>
  );
};

