// src/dataSource/pages/DataSourceDetails/index.tsx
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import type { AppDispatch } from '@/store/store';
import { Button } from '@/common/components/ui/button';
import { Alert, AlertDescription } from '@/common/components/ui/alert';
import { LoadingSpinner } from '@/common/components/navigation/LoadingSpinner';
import { ArrowLeft, RefreshCw, Trash2 } from 'lucide-react';
import { fetchDataSources, deleteDataSource } from '../../store/dataSourceSlice';
import { DataSourceType } from '../../types/base';
import { showNotification } from '@/common/components/layout/showNotifications';
import { useDataSource } from '../../hooks/useDataSource';
import { formatDate, getStatusColor } from './utils';
import {
  ApiSourceDetails,
  DBSourceDetails,
  FileSourceDetails,
  S3SourceDetails,
  StreamSourceDetails
} from './components';
import type { SourceMetadata } from './types';

const DataSourceDetailsPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { type, id } = useParams<{ type: string; id: string }>();
  
  const { 
    dataSources, 
    isLoading, 
    error,
    refreshDataSources,
    previewData,
    getPreview,
  } = useDataSource();

  const source = id ? dataSources[id] as SourceMetadata : null;

  useEffect(() => {
    console.log('DataSourceDetailsPage mounted', { type, id });
    dispatch(fetchDataSources());
  }, [dispatch, type, id]);

  const handleBack = () => {
    navigate(`/data-sources/${type}`);
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this data source?')) {
      return;
    }
    
    try {
      await dispatch(deleteDataSource(id!)).unwrap();
      showNotification({
        title: "Success",
        message: "Data source deleted successfully",
        type: "success",
      });
      navigate('/data-sources');
    } catch (err) {
      showNotification({
        title: "Error",
        message: "Failed to delete data source",
        type: "error",
      });
    }
  };

  const handleRefresh = () => {
    dispatch(fetchDataSources());
  };

  const handlePreview = async () => {
    if (!id) return;
    try {
      await getPreview(id, { limit: 10 });
    } catch (err) {
      showNotification({
        title: "Error",
        message: "Failed to load preview data",
        type: "error",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!source) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Data source not found</AlertDescription>
      </Alert>
    );
  }

  // Render specific details based on source type
  const renderSourceDetails = () => {
    switch (source.type) {
      case DataSourceType.API:
        return <ApiSourceDetails metadata={source as ApiMetadata} config={source as any} />;
      case DataSourceType.DATABASE:
        return <DBSourceDetails metadata={source as DBMetadata} config={source as any} />;
      case DataSourceType.FILE:
        return <FileSourceDetails metadata={source as FileMetadata} config={source as any} />;
      case DataSourceType.S3:
        return <S3SourceDetails metadata={source as S3Metadata} config={source as any} />;
      case DataSourceType.STREAM:
        return <StreamSourceDetails metadata={source as StreamMetadata} config={source as any} />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center">
            <Button
              variant="ghost"
              className="mr-4"
              onClick={handleBack}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <h1 className="text-xl font-semibold">{source.name}</h1>
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              onClick={handleRefresh}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </header>

      <main className="container">
        <div className="grid gap-6">
          {/* Basic Information */}
          <section className="rounded-lg border bg-card p-6">
            <h2 className="text-lg font-semibold mb-4">Basic Information</h2>
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Name</dt>
                <dd className="text-sm">{source.name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Type</dt>
                <dd className="text-sm capitalize">{source.type}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Status</dt>
                <dd className={`text-sm ${getStatusColor(source.status)}`}>
                  {source.status}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-muted-foreground">Last Sync</dt>
                <dd className="text-sm">{formatDate(source.lastSync)}</dd>
              </div>
              {source.description && (
                <div className="sm:col-span-2">
                  <dt className="text-sm font-medium text-muted-foreground">Description</dt>
                  <dd className="text-sm">{source.description}</dd>
                </div>
              )}
              {source.tags && source.tags.length > 0 && (
                <div className="sm:col-span-2">
                  <dt className="text-sm font-medium text-muted-foreground">Tags</dt>
                  <dd className="flex flex-wrap gap-2 mt-1">
                    {source.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                      >
                        {tag}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
            </dl>
          </section>

          {/* Source-specific details */}
          {renderSourceDetails()}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
      </main>
    </div>
  );
};

export default DataSourceDetailsPage;