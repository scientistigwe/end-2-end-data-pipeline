// src/pages/DataSourcesPage.tsx
import React, { useState } from "react";
import { useSelector } from "react-redux";
import { Routes, Route, useNavigate } from "react-router-dom";
import type { RootState } from "../store";
import type { SourceType, SourceTypeConfig } from "../hooks/dataSource/types";

// Components
import {
  FileSourceCard,
  ApiSourceCard,
  DBSourceCard,
  S3SourceCard,
  StreamSourceCard,
} from "../components/sources";

// Forms
import {
  FileSourceForm,
  APISourceForm,
  DBSourceForm,
  S3SourceForm,
  StreamSourceForm,
} from "../components/forms";

const SOURCE_TYPES: ReadonlyArray<SourceTypeConfig> = [
  { id: "file", label: "File" },
  { id: "api", label: "API" },
  { id: "database", label: "Database" },
  { id: "s3", label: "S3" },
  { id: "stream", label: "Stream" },
] as const;

export const DataSourcesPage: React.FC = () => {
  const navigate = useNavigate();
  const [sourceType, setSourceType] = useState<SourceType>("file");

  const activeSources = useSelector(
    (state: RootState) => state.dataSources.activeSources
  );

  const handleSourceTypeChange = (type: SourceType): void => {
    setSourceType(type);
    navigate(`/sources/${type}`);
  };

  const renderSourceForm = (): JSX.Element | null => {
    const forms: Record<SourceType, JSX.Element> = {
      file: <FileSourceForm />,
      api: <APISourceForm />,
      database: <DBSourceForm />,
      s3: <S3SourceForm />,
      stream: <StreamSourceForm />,
    };

    return forms[sourceType] ?? null;
  };

  const renderSourceList = (): JSX.Element[] => {
    const sourceComponents: Record<SourceType, React.FC<any>> = {
      file: FileSourceCard,
      api: ApiSourceCard,
      database: DBSourceCard,
      s3: S3SourceCard,
      stream: StreamSourceCard,
    };

    return Object.values(activeSources)
      .filter((source) => source.type === sourceType)
      .map((source) => {
        const SourceComponent = sourceComponents[source.type];
        return (
          <SourceComponent
            key={source.id}
            connectionId={source.id}
            {...(source.type === "file"
              ? { metadata: source.metadata }
              : { config: source.config })}
          />
        );
      });
  };

  return (
    <div className="space-y-6">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Data Sources</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Source Type Navigation */}
        <nav className="border-b border-gray-200">
          <div className="-mb-px flex space-x-8">
            {SOURCE_TYPES.map((type) => (
              <button
                key={type.id}
                onClick={() => handleSourceTypeChange(type.id)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm
                  ${
                    sourceType === type.id
                      ? "border-blue-500 text-blue-600"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  }
                `}
              >
                {type.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Source Configuration */}
        <section className="mt-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">
              Configure {sourceType.toUpperCase()} Source
            </h2>
            {renderSourceForm()}
          </div>
        </section>

        {/* Active Sources */}
        <section className="mt-6">
          <h2 className="text-lg font-medium mb-4">Active Sources</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderSourceList()}
          </div>
        </section>
      </main>

      <Routes>
        <Route path=":type" element={null} />
      </Routes>
    </div>
  );
};
