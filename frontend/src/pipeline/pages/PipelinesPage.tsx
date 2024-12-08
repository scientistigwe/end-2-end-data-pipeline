// src/pages/PipelinePage.tsx
import React from "react";
import { useSelector } from "react-redux";
import { PipelineCard } from "../components/pipeline/PipelineForm";
import { usePipeline } from "../hooks/dataPipeline/usePipeline";
import { RootState } from "../store";

export const PipelinesPage: React.FC = () => {
  const activePipelines = useSelector(
    (state: RootState) => state.pipelines.activePipelines
  );
  const { startPipeline } = usePipeline({});

  const handleCreatePipeline = () => {
    startPipeline({
      // Pipeline configuration
    });
  };

  return (
    <div className="space-y-6">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Pipelines</h1>
          <button
            onClick={handleCreatePipeline}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Create Pipeline
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Active Pipelines */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Active Pipelines</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.values(activePipelines).map((pipeline) => (
              <PipelineCard key={pipeline.id} pipelineId={pipeline.id} />
            ))}
          </div>
        </section>

        {/* Pipeline History */}
        <section className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Pipeline History</h2>
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pipeline ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Start Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {/* Pipeline history entries */}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
};
