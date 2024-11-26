import { useState, useCallback, useEffect, useRef } from "react";

const REFRESH_INTERVAL = 30000; // 30 seconds

const usePipeline = (apiClient) => {
  const [pipelines, setPipelines] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    total: 0,
    completed: 0,
    error: 0,
    waiting: 0,
    processing: 0,
  });
  const [shouldMonitorPipelines, setShouldMonitorPipelines] = useState(false);

  const lastRefreshRef = useRef(Date.now());
  const intervalRef = useRef(null);
  const isMountedRef = useRef(true);
  const fetchInProgressRef = useRef(false);

  // Calculate pipeline statistics
  const calculateStats = useCallback((pipelineData) => {
    const pipelineArray = Object.values(pipelineData);
    return {
      total: pipelineArray.length,
      completed: pipelineArray.filter((p) => p.status === "COMPLETED").length,
      error: pipelineArray.filter((p) => p.status === "ERROR").length,
      waiting: pipelineArray.filter((p) => p.status === "WAITING").length,
      processing: pipelineArray.filter((p) => p.status === "PROCESSING").length,
    };
  }, []);

  // Check if any pipelines are in progress
  const hasPipelinesInProgress = useCallback(() => {
    return Object.values(pipelines).some(
      (pipeline) =>
        pipeline.status === "PROCESSING" || pipeline.status === "WAITING"
    );
  }, [pipelines]);

  // Fetch pipeline status
  const fetchPipelineStatus = useCallback(async () => {
    if (fetchInProgressRef.current || !isMountedRef.current) return;

    fetchInProgressRef.current = true;
    try {
      setLoading(true);
      const response = await apiClient.getPipelineStatus();

      if (isMountedRef.current) {
        const activePipelines = response?.pipelines || {};
        setPipelines(activePipelines);
        setStats(calculateStats(activePipelines));
        lastRefreshRef.current = Date.now();
      }
    } catch (err) {
      if (isMountedRef.current) setError(err.message || "Error fetching pipeline status");
    } finally {
      fetchInProgressRef.current = false;
      if (isMountedRef.current) setLoading(false);
    }
  }, [apiClient, calculateStats]);

  // Dynamic refresh logic
  const managePipelineRefresh = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Check if we should monitor AND if there are pipelines in progress
    if (shouldMonitorPipelines && hasPipelinesInProgress()) {
      intervalRef.current = setInterval(() => {
        const timeSinceLastRefresh = Date.now() - lastRefreshRef.current;

        if (timeSinceLastRefresh >= REFRESH_INTERVAL) {
          fetchPipelineStatus();
        }
      }, REFRESH_INTERVAL);
    }

    // Cleanup function to clear interval
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetchPipelineStatus, hasPipelinesInProgress, shouldMonitorPipelines]);

  // Filter pipelines method
  const filterPipelines = useCallback(
    (filters = {}) => {
      return Object.fromEntries(
        Object.entries(pipelines).filter(([id, pipeline]) => {
          const matchesStatus = !filters.status || pipeline.status === filters.status;
          const matchesSearch =
            !filters.search ||
            id.toLowerCase().includes(filters.search.toLowerCase()) ||
            pipeline.status.toLowerCase().includes(filters.search.toLowerCase()) ||
            (pipeline.stages_completed || []).some((stage) =>
              stage.toLowerCase().includes(filters.search.toLowerCase())
            );
          return matchesStatus && matchesSearch;
        })
      );
    },
    [pipelines]
  );

  // Trigger monitoring after file upload
  const triggerPipelineMonitoring = useCallback(() => {
    console.log("Triggering pipeline monitoring");
    setShouldMonitorPipelines(true);
    fetchPipelineStatus();
  }, [fetchPipelineStatus]);

  // Start pipeline
  const startPipeline = useCallback(
    async (config) => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.startPipeline(config);

        // Immediately fetch status after starting
        await fetchPipelineStatus();

        // Set monitoring to true
        setShouldMonitorPipelines(true);

        return response;
      } catch (err) {
        setError(err.message || "Failed to start pipeline");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [apiClient, fetchPipelineStatus]
  );

  // Stop pipeline
  const stopPipeline = useCallback(
    async (pipelineId) => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.stopPipeline(pipelineId);

        await fetchPipelineStatus();

        // Disable monitoring if no pipelines in progress
        if (!hasPipelinesInProgress()) {
          setShouldMonitorPipelines(false);
        }

        return response;
      } catch (err) {
        setError(err.message || "Failed to stop pipeline");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [apiClient, fetchPipelineStatus, hasPipelinesInProgress]
  );

  // Initial and dynamic refresh setup
  useEffect(() => {
    isMountedRef.current = true;

    // Only fetch if monitoring is enabled and there are pipelines in progress
    if (shouldMonitorPipelines && hasPipelinesInProgress()) {
      fetchPipelineStatus();
    }

    // Set up dynamic refresh
    const cleanup = managePipelineRefresh();

    // Cleanup function
    return () => {
      isMountedRef.current = false;
      fetchInProgressRef.current = false;
      cleanup();
    };
  }, [fetchPipelineStatus, managePipelineRefresh, hasPipelinesInProgress, shouldMonitorPipelines]);

  return {
    pipelines,
    loading,
    error,
    stats,
    startPipeline,
    stopPipeline,
    filterPipelines,
    refreshPipelines: fetchPipelineStatus,
    triggerPipelineMonitoring,
  };
};

export default usePipeline;