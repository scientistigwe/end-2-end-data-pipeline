import { useState, useCallback, useEffect } from 'react';

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

  // Fetch pipeline status
  const fetchPipelineStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getPipelineStatus();
      setPipelines(response.pipelines || {});
      setStats(calculateStats(response.pipelines || {}));
    } catch (err) {
      setError(err.message || 'Failed to fetch pipeline status');
      console.error('Pipeline status error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiClient, calculateStats]);

  // Start pipeline
  const startPipeline = useCallback(async (config) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.startPipeline(config);
      await fetchPipelineStatus();
      return response;
    } catch (err) {
      setError(err.message || 'Failed to start pipeline');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiClient, fetchPipelineStatus]);

  // Stop pipeline
  const stopPipeline = useCallback(async (pipelineId) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.stopPipeline(pipelineId);
      await fetchPipelineStatus();
      return response;
    } catch (err) {
      setError(err.message || 'Failed to stop pipeline');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiClient, fetchPipelineStatus]);

  // Make pipeline decision
  const makePipelineDecision = useCallback(async (pipelineId, decision) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.makePipelineDecision(pipelineId, decision);
      await fetchPipelineStatus();
      return response;
    } catch (err) {
      setError(err.message || 'Failed to make pipeline decision');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiClient, fetchPipelineStatus]);

  // Get pipeline logs
  const getPipelineLogs = useCallback(async (pipelineId) => {
    try {
      const response = await apiClient.getPipelineLogs(pipelineId);
      return response;
    } catch (err) {
      setError(err.message || 'Failed to fetch pipeline logs');
      throw err;
    }
  }, [apiClient]);

  // Filter pipelines
  const filterPipelines = useCallback((filters = {}) => {
    return Object.entries(pipelines).filter(([id, pipeline]) => {
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
    }).reduce((acc, [id, pipeline]) => {
      acc[id] = pipeline;
      return acc;
    }, {});
  }, [pipelines]);

  // Auto-refresh pipeline status
  useEffect(() => {
    const intervalId = setInterval(fetchPipelineStatus, 5000);
    fetchPipelineStatus();

    return () => clearInterval(intervalId);
  }, [fetchPipelineStatus]);

  return {
    pipelines,
    loading,
    error,
    stats,
    startPipeline,
    stopPipeline,
    makePipelineDecision,
    getPipelineLogs,
    filterPipelines,
    refreshPipelines: fetchPipelineStatus
  };
};

export default usePipeline;