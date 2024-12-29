// src/dataSource/pages/DataSourceDetails/test-components.tsx
import React from "react";
import { Button } from "@/common/components/ui/button";
import { Alert } from "@/common/components/ui/alert";
import { LoadingSpinner } from "@/common/components/navigation/LoadingSpinner";
import type { ConnectionTestResponse } from "../../types/responses";

interface TestButtonProps {
  onTest: () => Promise<void>;
  isLoading: boolean;
}

interface TestResultProps {
  result: ConnectionTestResponse | null;
}

export const ConnectionTestButton: React.FC<TestButtonProps> = ({
  onTest,
  isLoading,
}) => (
  <Button variant="outline" onClick={onTest} disabled={isLoading}>
    {isLoading ? (
      <>
        <LoadingSpinner className="h-4 w-4 mr-2" />
        Testing...
      </>
    ) : (
      "Test Connection"
    )}
  </Button>
);

export const TestResultDisplay: React.FC<TestResultProps> = ({ result }) => {
  if (!result) return null;

  return (
    <Alert
      variant={result.success ? "default" : "destructive"}
      className="mt-4"
    >
      {result.success ? (
        <div className="flex items-center">
          <span className="font-medium">Connection successful</span>
          {result.responseTime && (
            <span className="ml-2 text-sm text-muted-foreground">
              ({result.responseTime}ms)
            </span>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="font-medium">Connection failed</p>
          {result.error && <p className="text-sm">{result.error.message}</p>}
        </div>
      )}
    </Alert>
  );
};
