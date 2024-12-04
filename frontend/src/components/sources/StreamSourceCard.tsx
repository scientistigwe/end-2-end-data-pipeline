
// src/pages/DataSourcesPage.tsx
import React, { useState } from 'react';
import { useSelector } from 'react-redux';
import { SourceCard } from '../components/sources/SourceCard';
import { useFileSource } from '../hooks/sources/useFileSource';
import { useApiSource } from '../hooks/sources/useApiSource';
import { useDBSource } from '../hooks/sources/useDBSource';
import { RootState } from '../store';

export const DataSourcesPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('file');
  const activeSources = useSelector((state: RootState) =>
    state.dataSources.activeSources
  );

  const { upload, uploadProgress } = useFileSource();
  const { connect: connectApi } = useApiSource();
  const { connect: connectDB } = useDBSource();

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      upload(Array.from(files));
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Data Sources</h1>

      {/* Source Type Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {['file', 'api', 'database', 's3', 'stream'].map(type => (
            <button
              key={type}
              onClick={() => setActiveTab(type)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === type
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
              `}
            >
              {type.toUpperCase()}
            </button>
          ))}
        </nav>
      </div>

      {/* Source Configuration */}
      <section className="bg-white rounded-lg shadow p-6">
        {activeTab === 'file' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Upload Files</h3>
            <input
              type="file"
              multiple
              onChange={handleFileUpload}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
            {uploadProgress > 0 && (
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'api' && (
          <form onSubmit={(e) => {
            e.preventDefault();
            // Handle API connection
          }}>
            {/* API configuration form */}
          </form>
        )}

        {/* Similar sections for other source types */}
      </section>

      {/* Active Sources */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Active Sources</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.values(activeSources)
            .filter(source => source.type === activeTab)
            .map(source => (
              <SourceCard
                key={source.id}
                sourceId={source.id}
                type={source.type}
                config={source.config}
              />
            ))}
        </div>
      </section>
    </div>
  );
};
