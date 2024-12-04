
const PipelineSettings: React.FC = () => {
  const [settings, setSettings] = useState({
    defaultBatchSize: 1000,
    maxConcurrentPipelines: 5,
    autoRetry: true,
    retryAttempts: 3
  });

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium text-gray-900">Pipeline Configuration</h2>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Default Batch Size
          </label>
          <input
            type="number"
            value={settings.defaultBatchSize}
            onChange={(e) => setSettings(prev => ({ ...prev, defaultBatchSize: parseInt(e.target.value) }))}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            Max Concurrent Pipelines
          </label>
          <input
            type="number"
            value={settings.maxConcurrentPipelines}
            onChange={(e) => setSettings(prev => ({ ...prev, maxConcurrentPipelines: parseInt(e.target.value) }))}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            checked={settings.autoRetry}
            onChange={(e) => setSettings(prev => ({ ...prev, autoRetry: e.target.checked }))}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label className="ml-2 block text-sm text-gray-900">
            Enable Auto-Retry
          </label>
        </div>

        {settings.autoRetry && (
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Retry Attempts
            </label>
            <input
              type="number"
              value={settings.retryAttempts}
              onChange={(e) => setSettings(prev => ({ ...prev, retryAttempts: parseInt(e.target.value) }))}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
        )}
      </div>
    </div>
  );
};
