// src/pipeline/components/PipelineBreadcrumbs.tsx
import React from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { usePipeline } from "../hooks/usePipeline";

export const PipelineBreadcrumbs: React.FC = () => {
  const { id } = useParams();
  const { pipeline } = usePipeline(id);

  return (
    <nav className="flex items-center space-x-2 text-sm">
      <Link
        to={PIPELINE_ROUTES.LIST}
        className="text-gray-600 hover:text-gray-900"
      >
        Pipelines
      </Link>

      {id && (
        <>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <Link
            to={getPipelinePathWithId(PIPELINE_ROUTES.DETAILS, id)}
            className="text-gray-600 hover:text-gray-900"
          >
            {pipeline?.name || id}
          </Link>
        </>
      )}

      {id && window.location.pathname.includes("/runs") && (
        <>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <span className="text-gray-900">Runs</span>
        </>
      )}

      {id && window.location.pathname.includes("/metrics") && (
        <>
          <ChevronRight className="h-4 w-4 text-gray-400" />
          <span className="text-gray-900">Metrics</span>
        </>
      )}
    </nav>
  );
};
