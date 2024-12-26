// src/dataSource/context/DataSourceContext.tsx
import { createContext, useContext } from "react";
import type {
  DataSourceMetadata,
  DataSourceConfig,
  DataSourceFilters,
  ValidationResult,
  PreviewData,
} from "../types/base";

interface DataSourceContextValue {
  // State
  dataSources: DataSourceMetadata[];
  selectedSource: DataSourceConfig | null;
  filters: DataSourceFilters;
  previewData: PreviewData | null;
  validationResult: ValidationResult | null;
  isLoading: boolean;
  error: Error | null;

  // Actions
  loadDataSources: (filters?: DataSourceFilters) => Promise<void>;
  createDataSource: (config: DataSourceConfig) => Promise<void>;
  updateDataSource: (
    id: string,
    updates: Partial<DataSourceConfig>
  ) => Promise<void>;
  deleteDataSource: (id: string) => Promise<void>;
  validateDataSource: (id: string) => Promise<void>;
  previewDataSource: (
    id: string,
    options?: { limit?: number; offset?: number }
  ) => Promise<void>;
  setFilters: (filters: DataSourceFilters) => void;
  selectDataSource: (source: DataSourceConfig | null) => void;
  clearError: () => void;
}

export const DataSourceContext = createContext<
  DataSourceContextValue | undefined
>(undefined);

export const useDataSourceContext = () => {
  const context = useContext(DataSourceContext);
  if (!context) {
    throw new Error(
      "useDataSourceContext must be used within a DataSourceProvider"
    );
  }
  return context;
};
