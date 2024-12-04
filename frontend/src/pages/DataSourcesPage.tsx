// src/pages/DataSourcesPage.tsx
import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { FileSourceCard } from '../components/sources/FileSourceCard';
import { ApiSourceCard } from '../components/sources/ApiSourceCard';
import { DBSourceCard } from '../components/sources/DBSourceCard';
import { S3SourceCard } from '../components/sources/S3SourceCard';
import { StreamSourceCard } from '../components/sources/StreamSourceCard';
import { useFileSource } from '../hooks/sources/useFileSource';
import { useApiSource } from '../hooks/sources/useApiSource';
import { useDBSource } from '../hooks/sources/useDBSource';
import { useS3Source } from '../hooks/sources/useS3Source';
import { useStreamSource } from '../hooks/sources/useStreamSource';
import { RootState } from '../store';

const sourceTypes = [
  { id: 'file', label: 'File' },
  { id: 'api', label: 'API' },
  { id: 'database', label: 'Database' },
  { id: 's3', label: 'S3' },
  { id: 'stream', label: 'Stream' }
] as const;

export const DataSourcesPage: React.FC = () => {
  const navigate = useNavigate();
  const activeSources = useSelector((state: RootState) => state.dataSources.activeSources);
  const [sourceType, setSourceType] = useState<typeof sourceTypes[number]['id']>('file');

  const handleSourceTypeChange = (type: typeof sourceTypes[number]['id']) => {
    setSourceType(type);
    navigate(`/sources/${type}`);
  };

  const renderSourceForm = () => {
    switch (sourceType) {
      case 'file':
        return <FileSourceForm />;
      case 'api':
        return <ApiSourceForm />;
      case 'database':
        return <DBSourceForm />;
      case 's3':
        return <S3SourceForm />;
      case 'stream':
        return <StreamSourceForm />;
      default:
        return null;
    }
  };

  const renderSourceList = () => {
    return Object.values(activeSources)
      .filter(source => source.type === sourceType)
      .map(source => {
        switch (source.type) {
          case 'file':
            return (
              <FileSourceCard
                key={source.id}
                fileId={source.id}
                metadata={source.metadata}
              />
            );
          case 'api':
            return (
              <ApiSourceCard
                key={source.id}
                connectionId={source.id}
                config={source.config}
              />
            );
          case 'database':
            return (
              <DBSourceCard
                key={source.id}
                connectionId={source.id}
                config={source.config}
              />
            );
          case 's3':
            return (
              <S3SourceCard
                key={source.id}
                connectionId={source.id}
                config={source.config}
              />
            );
          case 'stream':
            return (
              <StreamSourceCard
                key={source.id}
                connectionId={source.id}
                config={source.config}
              />
            );
          default:
            return null;
        }
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
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {sourceTypes.map(type => (
              <button
                key={type.id}
                onClick={() => handleSourceTypeChange(type.id)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm
                  ${sourceType === type.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
                `}
              >
                {type.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Source Configuration Section */}
        <section className="mt-6">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">Configure {sourceType.toUpperCase()} Source</h2>
            {renderSourceForm()}
          </div>
        </section>

        {/* Active Sources Section */}
        <section className="mt-6">
          <h2 className="text-lg font-medium mb-4">Active Sources</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {renderSourceList()}
          </div>
        </section>
      </main>

      {/* Routes for nested pages */}
      <Routes>
        <Route path=":type" element={null} />
      </Routes>
    </div>
  );
};