import { useState, useCallback, useEffect, useRef } from 'react';

const usePipeline = (apiClient) => {
  const [pipelines, setPipelines] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    total: 0,
    completed: 0,
    error: 0,
    waiting: 0,
    processing: 0
  });

  // Ref to track the last refresh time
  const lastRefreshRef = useRef(Date.now());
  // Ref to track the current interval ID
  const intervalRef = useRef(null);

  // Calculate pipeline statistics
  const calculateStats = useCallback((pipelineData) => {
    const pipelineArray = Object.values(pipelineData);
    return {
      total: pipelineArray.length,
      completed: pipelineArray.filter(p => p.status === 'COMPLETED').length,
      error: pipelineArray.filter(p => p.status === 'ERROR').length,
      waiting: pipelineArray.filter(p => p.status === 'WAITING').length,
      processing: pipelineArray.filter(p => p.status === 'PROCESSING').length
    };
  }, []);

  // Check if any pipelines are in progress
  const hasPipelinesInProgress = useCallback(() => {
    return Object.values(pipelines).some(
      pipeline =>
        pipeline.status === 'PROCESSING' ||
        pipeline.status === 'WAITING'
    );
  }, [pipelines]);

  // Fetch pipeline status
  const fetchPipelineStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getPipelineStatus();
      setPipelines(response.pipelines || {});
      setStats(calculateStats(response.pipelines || {}));

      // Update last refresh time
      lastRefreshRef.current = Date.now();
    } catch (err) {
      setError(err.message || 'Failed to fetch pipeline status');
      console.error('Pipeline status error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiClient, calculateStats]);

  // Filter pipelines method
  const filterPipelines = useCallback((filters = {}) => {
    return Object.entries(pipelines)
      .filter(([id, pipeline]) => {
        if (filters.status && pipeline.status !== filters.status) return false;
        if (filters.search) {
          const searchLower = filters.search.toLowerCase();
          return (
            id.toLowerCase().includes(searchLower) ||
            pipeline.status.toLowerCase().includes(searchLower) ||
            (pipeline.stages_completed || []).some(stage =>
              stage.toLowerCase().includes(searchLower)
            )
          );
        }
        return true;
      })
      .reduce((acc, [id, pipeline]) => {
        acc[id] = pipeline;
        return acc;
      }, {});
  }, [pipelines]);

  // Dynamic refresh logic
  const managePipelineRefresh = useCallback(() => {
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Check if there are pipelines in progress
    const inProgress = hasPipelinesInProgress();

    if (inProgress) {
      // If pipelines are in progress, set interval to 30 seconds
      intervalRef.current = setInterval(() => {
        const timeSinceLastRefresh = Date.now() - lastRefreshRef.current;

        // Additional check to ensure we're still in progress
        if (hasPipelinesInProgress() && timeSinceLastRefresh >= 30000) {
          fetchPipelineStatus();
        }
      }, 30000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchPipelineStatus, hasPipelinesInProgress]);

  // Start pipeline
  const startPipeline = useCallback(async (config) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.startPipeline(config);

      // Immediately fetch status after starting
      await fetchPipelineStatus();

      // Set up refresh based on new pipeline status
      managePipelineRefresh();

      return response;
    } catch (err) {
      setError(err.message || 'Failed to start pipeline');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiClient, fetchPipelineStatus, managePipelineRefresh]);

  // Other methods remain similar
  const stopPipeline = useCallback(async (pipelineId) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.stopPipeline(pipelineId);
      await fetchPipelineStatus();

      // Reconfigure refresh after stopping
      managePipelineRefresh();

      return response;
    } catch (err) {
      setError(err.message || 'Failed to stop pipeline');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiClient, fetchPipelineStatus, managePipelineRefresh]);

  const makePipelineDecision = useCallback(async (pipelineId, decision) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.makePipelineDecision(pipelineId, decision);
      await fetchPipelineStatus();

      // Reconfigure refresh after decision
      managePipelineRefresh();

      return response;
    } catch (err) {
      setError(err.message || 'Failed to make pipeline decision');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiClient, fetchPipelineStatus, managePipelineRefresh]);

  // File source upload hook integration
  const triggerRefreshOnFileUpload = useCallback((response) => {
    if (response) {
      fetchPipelineStatus();
      managePipelineRefresh();
    }
  }, [fetchPipelineStatus, managePipelineRefresh]);

  // Initial and dynamic refresh setup
  useEffect(() => {
    // Initial fetch and setup
    fetchPipelineStatus();

    // Dynamic refresh based on pipeline status
    const cleanup = managePipelineRefresh();

    return cleanup;
  }, [fetchPipelineStatus, managePipelineRefresh]);

  return {
    pipelines,
    loading,
    error,
    stats,
    startPipeline,
    stopPipeline,
    makePipelineDecision,
    triggerRefreshOnFileUpload,
    filterPipelines,  // Explicitly added back to the returned object
    refreshPipelines: fetchPipelineStatus
  };
};

export default usePipeline;