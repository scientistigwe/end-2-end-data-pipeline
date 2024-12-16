import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import {
  PlusIcon,
  FileIcon,
  GlobeIcon,
  DatabaseIcon,
  CloudIcon,
  ActivityIcon,
} from "lucide-react";
import { Button } from "@/common/components/ui/button";
import { Alert, AlertDescription } from "@/common/components/ui/alert";
import { LoadingSpinner } from "@/common/components/navigation/LoadingSpinner";
import { cn } from "@/common/utils/cn";
import { showNotification } from "@/common/components/layout/showNotifications";
import {
  fetchDataSources,
  deleteDataSource,
  createDataSource,
} from "../store/dataSourceSlice";
import type { AppDispatch, RootState } from "@/store/store";
import type {
  DataSourceType,
  DataSourceConfig,
  ApiSourceConfig, // Import ApiSourceConfig type
} from "../types/dataSources";

// Components
import {
  FileSourceCard,
  ApiSourceCard,
  DBSourceCard,
  S3SourceCard,
  StreamSourceCard,
} from "../components/cards";

import {
  FileSourceForm,
  ApiSourceForm,
  DBSourceForm,
  S3SourceForm,
  StreamSourceForm,
} from "../components/forms";

interface SourceTypeConfig {
  id: DataSourceType;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const SOURCE_TYPES: SourceTypeConfig[] = [
  {
    id: "file",
    label: "File Upload",
    description: "Upload and process local files",
    icon: <FileIcon className="h-5 w-5" />,
  },
  {
    id: "api",
    label: "API",
    description: "Connect to REST or GraphQL APIs",
    icon: <GlobeIcon className="h-5 w-5" />,
  },
  {
    id: "database",
    label: "Database",
    description: "Connect to SQL and NoSQL databases",
    icon: <DatabaseIcon className="h-5 w-5" />,
  },
  {
    id: "s3",
    label: "S3 Storage",
    description: "Access cloud storage services",
    icon: <CloudIcon className="h-5 w-5" />,
  },
  {
    id: "stream",
    label: "Data Stream",
    description: "Process real-time data streams",
    icon: <ActivityIcon className="h-5 w-5" />,
  },
];

const DataSourcesPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { type } = useParams<{ type?: string }>();
  const [isCreating, setIsCreating] = useState(false);

  const sources = useSelector((state: RootState) => state.dataSources.sources);
  const isLoading = useSelector(
    (state: RootState) => state.dataSources.isLoading
  );
  const error = useSelector((state: RootState) => state.dataSources.error);

  const currentType = type as DataSourceType | undefined;

  useEffect(() => {
    if (!currentType && SOURCE_TYPES.length > 0) {
      navigate(`/sources/${SOURCE_TYPES[0].id}`);
    }
  }, [currentType, navigate]);

  useEffect(() => {
    dispatch(fetchDataSources());
  }, [dispatch]);

  const handleTypeChange = (newType: DataSourceType) => {
    navigate(`/sources/${newType}`);
    setIsCreating(false);
  };

  const handleCreateSource = () => {
    setIsCreating(true);
  };

  const handleCancelCreate = () => {
    setIsCreating(false);
  };

  const handleSourceSubmit = async (
    config: ApiSourceConfig | DataSourceConfig
  ) => {
    try {
      await dispatch(createDataSource(config)).unwrap();
      setIsCreating(false);
      showNotification({
        title: "Success",
        message: "Data source created successfully",
        type: "success",
      });
    } catch (err) {
      showNotification({
        title: "Error",
        message: "Failed to create data source",
        type: "error",
      });
    }
  };

  const renderSourceForm = () => {
    if (!currentType) return null;

    const formProps = {
      onSubmit: handleSourceSubmit,
      onCancel: handleCancelCreate,
    };

    const forms: Record<DataSourceType, React.ReactNode> = {
      file: <FileSourceForm {...formProps} />,
      api: (
        <ApiSourceForm
          onSubmit={handleSourceSubmit}
          onCancel={handleCancelCreate}
        />
      ),
      database: (
        <DBSourceForm
          onSubmit={handleSourceSubmit}
          onCancel={handleCancelCreate}
        />
      ),
      s3: (
        <S3SourceForm
          onSubmit={handleSourceSubmit}
          onCancel={handleCancelCreate}
        />
      ),
      stream: (
        <StreamSourceForm
          onSubmit={handleSourceSubmit}
          onCancel={handleCancelCreate}
        />
      ),
    };

    return forms[currentType];
  };

  const renderSourceCards = () => {
    if (!currentType) return null;

    const sourcesByType = Object.entries(sources)
      .filter(([_, source]) => source.type === currentType)
      .map(([_, source]) => source);

    const cards: Record<DataSourceType, React.ComponentType<any>> = {
      file: FileSourceCard,
      api: ApiSourceCard,
      database: DBSourceCard,
      s3: S3SourceCard,
      stream: StreamSourceCard,
    };

    return sourcesByType.map((source) => {
      const SourceCard = cards[source.type];
      return (
        <SourceCard
          key={source.id}
          source={source}
          onDelete={handleDeleteSource}
        />
      );
    });
  };

  const handleDeleteSource = async (sourceId: string) => {
    try {
      await dispatch(deleteDataSource(sourceId)).unwrap();
      showNotification({
        title: "Success",
        message: "Data source deleted successfully",
        type: "success",
      });
    } catch (err) {
      showNotification({
        title: "Error",
        message: "Failed to delete data source",
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

  return (
    <div className="space-y-8">
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center">
          <div className="flex flex-1">
            <h1 className="text-xl font-semibold">Data Sources</h1>
          </div>
          <div className="flex items-center space-x-4">
            <Button
              onClick={handleCreateSource}
              disabled={isCreating || !currentType}
            >
              <PlusIcon className="mr-2 h-4 w-4" />
              Add Source
            </Button>
          </div>
        </div>
      </header>

      <main className="container">
        <div className="flex space-x-12">
          <aside className="w-64 shrink-0">
            <nav className="space-y-2 sticky top-4">
              {SOURCE_TYPES.map((sourceType) => (
                <button
                  key={sourceType.id}
                  onClick={() => handleTypeChange(sourceType.id)}
                  className={cn(
                    "flex w-full items-center space-x-4 rounded-lg px-4 py-2",
                    "transition-colors hover:bg-accent",
                    currentType === sourceType.id
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {sourceType.icon}
                  <div className="flex-1 text-left">
                    <p className="text-sm font-medium">{sourceType.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {sourceType.description}
                    </p>
                  </div>
                </button>
              ))}
            </nav>
          </aside>

          <div className="flex-1 space-y-8">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {isCreating ? (
              <div className="rounded-lg border bg-card">
                <div className="p-6">
                  <h2 className="text-lg font-semibold mb-6">
                    Create{" "}
                    {SOURCE_TYPES.find((t) => t.id === currentType)?.label}
                  </h2>
                  {renderSourceForm()}
                </div>
              </div>
            ) : (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {renderSourceCards()}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default DataSourcesPage;
