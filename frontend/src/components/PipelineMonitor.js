import React, { useState, useEffect, useCallback, useMemo } from 'react';
import usePipeline from '../hooks/usePipeline';
import ApiClient from '../utils/api-client';
import {
  Card,
  CardContent,
  CardHeader,
  CardActions,
  Typography,
  Button,
  Badge,
  Select,
  MenuItem,
  InputBase,
  CircularProgress,
  Alert,
  AlertTitle,
  IconButton,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  WatchLater as WatchLaterIcon,
  PlayCircleOutline as ProcessingIcon,
  Warning as WarningIcon,
  Search as SearchIcon,
} from '@mui/icons-material';

const PipelineMonitor = () => {
  // Initialize API client
  const [apiClient] = useState(() => new ApiClient('http://127.0.0.1:5000'));
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const {
    pipelines,
    loading,
    error,
    stats,
    makePipelineDecision,
    filterPipelines,
    refreshPipelines,
  } = usePipeline(apiClient);

  // Memoize filtered pipelines
  const filteredPipelines = useMemo(() =>
    filterPipelines({
      status: statusFilter,
      search: searchTerm,
    }),
    [filterPipelines, statusFilter, searchTerm]
  );

  // Determine if any active pipelines exist
  const hasActivePipelines = useMemo(() =>
    Object.values(pipelines).some(pipeline =>
      ['WAITING', 'PROCESSING'].includes(pipeline.status)
    ),
    [pipelines]
  );

  // Auto-refresh logic with reduced frequency for active pipelines
  useEffect(() => {
    // Only set up auto-refresh if there are active pipelines
    if (!hasActivePipelines) return;

    const refreshInterval = setInterval(() => {
      refreshPipelines();
    }, 10000); // Reduced to every 10 seconds when active

    return () => clearInterval(refreshInterval);
  }, [hasActivePipelines, refreshPipelines]);

  const getStatusIcon = useCallback((status) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircleIcon color="success" />;
      case 'ERROR':
        return <ErrorIcon color="error" />;
      case 'WAITING':
        return <WatchLaterIcon color="warning" />;
      case 'PROCESSING':
        return <ProcessingIcon color="info" className="animate-spin" />;
      default:
        return <WarningIcon color="disabled" />;
    }
  }, []);

  const handleDecision = useCallback(async (pipelineId, decision) => {
    try {
      await makePipelineDecision(pipelineId, decision);
    } catch (err) {
      console.error('Decision error:', err);
    }
  }, [makePipelineDecision]);

  // Render the component
  return (
    <div style={{ padding: '24px' }}>
      {/* Header with Stats */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4">Pipeline Monitor</Typography>
          <IconButton
            onClick={refreshPipelines}
            disabled={loading}
          >
            <RefreshIcon />
          </IconButton>
        </div>

        {/* Stats Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px', marginTop: '16px' }}>
          {Object.entries({
            Total: { value: stats.total, color: 'textPrimary' },
            Completed: { value: stats.completed, color: 'success.main' },
            Errors: { value: stats.error, color: 'error.main' },
            Waiting: { value: stats.waiting, color: 'warning.main' },
            Processing: { value: stats.processing, color: 'info.main' },
          }).map(([label, { value, color }]) => (
            <Card key={label}>
              <CardContent>
                <Typography variant="h5" style={{ color }}>
                  {value}
                </Typography>
                <Typography variant="subtitle2" color="textSecondary">
                  {label}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Search and Filter Controls */}
        <div style={{ display: 'flex', gap: '16px', marginTop: '16px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <SearchIcon style={{ position: 'absolute', top: '8px', left: '8px', color: 'gray' }} />
            <InputBase
              placeholder="Search pipelines..."
              style={{ paddingLeft: '32px', width: '100%' }}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            displayEmpty
            style={{ minWidth: '160px' }}
          >
            <MenuItem value="">All Status</MenuItem>
            <MenuItem value="COMPLETED">Completed</MenuItem>
            <MenuItem value="ERROR">Error</MenuItem>
            <MenuItem value="WAITING">Waiting</MenuItem>
            <MenuItem value="PROCESSING">Processing</MenuItem>
          </Select>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" style={{ marginBottom: '16px' }}>
          <AlertTitle>Error</AlertTitle>
          {error}
        </Alert>
      )}

      {/* Pipeline Cards */}
      <div>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px' }}>
            <CircularProgress />
            <Typography variant="body2" color="textSecondary">
              Loading pipelines...
            </Typography>
          </div>
        ) : (
          Object.entries(filteredPipelines).map(([pipelineId, pipeline]) => (
            <Card key={pipelineId} style={{ marginBottom: '16px' }}>
              <CardHeader
                title={`Pipeline ${pipelineId}`}
                avatar={getStatusIcon(pipeline.status)}
                action={
                  <Badge
                    badgeContent={pipeline.status}
                    color={pipeline.status === 'COMPLETED' ? 'success' : 'default'}
                  />
                }
              />
              <CardContent>
                <Typography variant="body2" color="textSecondary">
                  Start Time: {new Date(pipeline.start_time).toLocaleString()}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Duration: {pipeline.current_duration}s
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Stages Completed: {pipeline.stages_completed?.join(' → ') || 'None'}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Data Size: {pipeline.data_size} bytes
                </Typography>

                {pipeline.recommendations?.length > 0 && (
                  <div style={{ marginTop: '16px' }}>
                    <Typography variant="body2" color="textSecondary">
                      Recommendations:
                    </Typography>
                    <ul>
                      {pipeline.recommendations.map((rec, idx) => (
                        <li key={idx}>
                          <Typography variant="body2">{rec}</Typography>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
              {pipeline.status === 'WAITING' && (
                <CardActions>
                  <Button onClick={() => handleDecision(pipelineId, true)} variant="contained" color="primary">
                    Proceed
                  </Button>
                  <Button onClick={() => handleDecision(pipelineId, false)} variant="outlined" color="error">
                    Stop
                  </Button>
                </CardActions>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default PipelineMonitor;