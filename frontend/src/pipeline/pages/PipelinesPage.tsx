// src/pipeline/pages/PipelinesPage.tsx
import React, { useState, useMemo, useCallback } from "react";
import { useSelector } from "react-redux";
import { Button } from "@/common/components/ui/button";
import { Input } from "@/common/components/ui/inputs/input";
import { Select } from "@/common/components/ui/inputs/select";
import { PipelineList } from "../components/PipelineList";
import { PipelineForm } from "../components/PipelineForm";
import { usePipeline } from "../hooks/usePipeline";
import { useModal } from "@/common/hooks/useModal";
import { PIPELINE_CONSTANTS } from "../constants";
import { selectModalById } from "@/common/store/ui/selectors";
import type { PipelineConfig, PipelineStatus, PipelineMode } from "../types/pipeline";

const MODAL_ID = 'create-pipeline-modal';

interface FilterState {
  status: PipelineStatus | "";
  mode: PipelineMode | "";
  search: string;
}

interface FormState {
  initialData?: PipelineConfig;
  isDirty: boolean;
  error?: string | null;
}

const PipelinesPage: React.FC = () => {
  // Global hooks
  const { pipelines, createPipeline: { mutateAsync: createPipeline }, isLoading } = usePipeline();
  const activeModal = useSelector(selectModalById(MODAL_ID));

  // Local state
  const [filters, setFilters] = useState<FilterState>({
    status: "",
    mode: "",
    search: "",
  });

  const [formState, setFormState] = useState<FormState>({
    initialData: undefined,
    isDirty: false,
    error: null
  });

  // Modal handlers
  const handleModalOpen = useCallback(() => {
    setFormState({
      initialData: {
        name: '',
        mode: 'development',
        steps: [],
        sourceId: '',
        description: ''
      },
      isDirty: false,
      error: null
    });
  }, []);

  const handleModalClose = useCallback(() => {
    if (formState.isDirty) {
      const confirm = window.confirm('You have unsaved changes. Are you sure you want to close?');
      if (!confirm) return false;
    }
    
    setFormState({
      initialData: undefined,
      isDirty: false,
      error: null
    });

    return true;
  }, [formState.isDirty]);

  const modal = useModal({
    id: MODAL_ID,
    onOpen: handleModalOpen,
    onClose: handleModalClose
  });

  // Check if our modal is active
  const isModalOpen = Boolean(activeModal);

  // Pipeline handlers
  const handleCreatePipeline = async (data: PipelineConfig) => {
    try {
      await createPipeline(data);
      setFormState(prev => ({ ...prev, isDirty: false, error: null }));
      modal.close();
    } catch (error) {
      console.error('Failed to create pipeline:', error);
      setFormState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to create pipeline'
      }));
    }
  };

  const handleFormChange = useCallback((isDirty: boolean) => {
    setFormState(prev => ({ ...prev, isDirty, error: null }));
  }, []);

  // Filter handlers
  const handleFilterChange = useCallback((
    key: keyof FilterState,
    value: string
  ) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleResetFilters = useCallback(() => {
    setFilters({
      status: "",
      mode: "",
      search: "",
    });
  }, []);

  // Memoized filtered pipelines
  const filteredPipelines = useMemo(() => {
    if (!pipelines) return [];

    return pipelines.filter((pipeline) => {
      const statusMatch = !filters.status || pipeline.status === filters.status;
      const modeMatch = !filters.mode || pipeline.mode === filters.mode;
      const searchMatch = !filters.search || 
        pipeline.name.toLowerCase().includes(filters.search.toLowerCase());

      return statusMatch && modeMatch && searchMatch;
    });
  }, [pipelines, filters]);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
        event.preventDefault();
        if (!isModalOpen) modal.open();
      }
      if (event.key === 'Escape' && isModalOpen) {
        modal.close();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isModalOpen, modal]);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Pipelines</h1>
        <div className="space-x-2">
          {Object.values(filters).some(Boolean) && (
            <Button 
              variant="outline" 
              onClick={handleResetFilters}
            >
              Reset Filters
            </Button>
          )}
          <Button 
            onClick={() => modal.open()}
            disabled={isLoading}
          >
            Create Pipeline
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex space-x-4">
        <Input
          placeholder="Search pipelines..."
          value={filters.search}
          onChange={(e) => handleFilterChange('search', e.target.value)}
          className="max-w-xs"
        />
        <Select
          value={filters.status}
          onChange={(e) => handleFilterChange('status', e.target.value as PipelineStatus)}
          className="w-[200px]"
        >
          <option value="">All Status</option>
          {Object.entries(PIPELINE_CONSTANTS.STATUS).map(([key, value]) => (
            <option key={value} value={value}>
              {key.charAt(0).toUpperCase() + key.slice(1).toLowerCase()}
            </option>
          ))}
        </Select>
        <Select
          value={filters.mode}
          onChange={(e) => handleFilterChange('mode', e.target.value as PipelineMode)}
          className="w-[200px]"
        >
          <option value="">All Modes</option>
          {Object.entries(PIPELINE_CONSTANTS.MODES).map(([key, value]) => (
            <option key={value} value={value}>
              {key.charAt(0).toUpperCase() + key.slice(1).toLowerCase()}
            </option>
          ))}
        </Select>
      </div>

      {/* Pipeline List */}
      <PipelineList 
        pipelines={filteredPipelines} 
        isLoading={isLoading}
      />

      {/* Create Pipeline Modal */}
      {isModalOpen && (
        <PipelineForm
          initialData={formState.initialData}
          onSubmit={handleCreatePipeline}
          onCancel={() => modal.close()}
          onChange={handleFormChange}
          isLoading={isLoading}
          error={formState.error}
        />
      )}
    </div>
  );
};

export default PipelinesPage