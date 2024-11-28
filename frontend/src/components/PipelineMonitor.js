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

// Stats Card Component
const StatCard = ({ label, value, color }) => (
  <Card>
    <CardContent>
      <Typography variant="h5" style={{ color }}>
        {value}
      </Typography>
      <Typography variant="subtitle2" color="textSecondary">
        {label}
      </Typography>
    </CardContent>
  </Card>
);

// Search Controls Component
const SearchControls = ({ searchTerm, setSearchTerm, statusFilter, setStatusFilter }) => (
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
);

// Pipeline Stage Info Component
const StageInfo = ({ staging }) => (
  <div style={{ marginBottom: '16px' }}>
    <Typography variant="subtitle2" color="primary">
      Stage Progress
    </Typography>
    <Typography variant="body2">
      {staging.current_stage}: {staging.stage_status}
    </Typography>
    {staging.next_stage && (
      <Typography variant="body2" color="textSecondary">
        Next Stage: {staging.next_stage}
      </Typography>
    )}
  </div>
);

// User Decision Component
const UserDecision = ({ pipelineId, decisionMessage, onDecision }) => (
  <Alert severity="info" style={{ marginTop: '16px' }}>
    <AlertTitle>Action Required</AlertTitle>
    {decisionMessage}
    <div style={{ marginTop: '16px' }}>
      <Button
        variant="contained"
        color="primary"
        onClick={() => onDecision(pipelineId, true)}
        style={{ marginRight: '8px' }}
      >
        Proceed
      </Button>
      <Button
        variant="outlined"
        color="error"
        onClick={() => onDecision(pipelineId, false)}
      >
        Stop
      </Button>
    </div>
  </Alert>
);

// Pipeline Card Component
const PipelineCard = ({ pipeline, pipelineId, getStatusIcon, onDecision }) => (
  <Card style={{ marginBottom: '16px' }}>
    <CardHeader
      title={`Pipeline ${pipelineId}`}
      avatar={getStatusIcon(pipeline.status)}
      subheader={`Current Stage: ${pipeline.staging?.current_stage || 'Initializing'}`}
    />
    <CardContent>
      {pipeline.staging && <StageInfo staging={pipeline.staging} />}

      {pipeline.staging?.requires_decision && (
        <UserDecision
          pipelineId={pipelineId}
          decisionMessage={pipeline.staging.decision_message}
          onDecision={onDecision}
        />
      )}

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
        <Button
          onClick={() => onDecision(pipelineId, true)}
          variant="contained"
          color="primary"
        >
          Proceed
        </Button>
        <Button
          onClick={() => onDecision(pipelineId, false)}
          variant="outlined"
          color="error"
        >
          Stop
        </Button>
      </CardActions>
    )}
  </Card>
);

// Main PipelineMonitor Component
const PipelineMonitor = () => {
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

  const filteredPipelines = useMemo(() =>
    filterPipelines({
      status: statusFilter,
      search: searchTerm,
    }),
    [filterPipelines, statusFilter, searchTerm]
  );

  const hasActivePipelines = useMemo(() =>
    Object.values(pipelines).some(pipeline =>
      ['WAITING', 'PROCESSING'].includes(pipeline.status)
    ),
    [pipelines]
  );

  const isEmpty = useMemo(() =>
    Object.keys(pipelines).length === 0,
    [pipelines]
  );

  useEffect(() => {
    if (!hasActivePipelines) return;

    const refreshInterval = setInterval(() => {
      refreshPipelines();
    }, 10000);

    return () => clearInterval(refreshInterval);
  }, [hasActivePipelines, refreshPipelines]);

  const getStatusIcon = useCallback((status) => {
    const icons = {
      COMPLETED: <CheckCircleIcon color="success" />,
      ERROR: <ErrorIcon color="error" />,
      WAITING: <WatchLaterIcon color="warning" />,
      PROCESSING: <ProcessingIcon color="info" className="animate-spin" />,
    };
    return icons[status] || <WarningIcon color="disabled" />;
  }, []);

  const handleDecision = useCallback(async (pipelineId, decision) => {
    try {
      await makePipelineDecision(pipelineId, decision);
    } catch (err) {
      console.error('Decision error:', err);
    }
  }, [makePipelineDecision]);

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h4">Pipeline Monitor</Typography>
          <IconButton onClick={refreshPipelines} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px', marginTop: '16px' }}>
          {Object.entries({
            Total: { value: stats.total, color: 'textPrimary' },
            Completed: { value: stats.completed, color: 'success.main' },
            Errors: { value: stats.error, color: 'error.main' },
            Waiting: { value: stats.waiting, color: 'warning.main' },
            Processing: { value: stats.processing, color: 'info.main' },
          }).map(([label, stats]) => (
            <StatCard key={label} label={label} {...stats} />
          ))}
        </div>

        <SearchControls
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
        />
      </div>

      {error && (
        <Alert severity="error" style={{ marginBottom: '16px' }}>
          <AlertTitle>Error</AlertTitle>
          {error}
        </Alert>
      )}

      <div>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px' }}>
            <CircularProgress />
            <Typography variant="body2" color="textSecondary">
              Loading pipelines...
            </Typography>
          </div>
        ) : isEmpty ? (
          <Card style={{ textAlign: 'center', padding: '32px', marginTop: '24px' }}>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              No Active Pipelines
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Upload a file to start processing or check back later for pipeline activity.
            </Typography>
          </Card>
        ) : (
          Object.entries(filteredPipelines).map(([pipelineId, pipeline]) => (
            <PipelineCard
              key={pipelineId}
              pipeline={pipeline}
              pipelineId={pipelineId}
              getStatusIcon={getStatusIcon}
              onDecision={handleDecision}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default PipelineMonitor;