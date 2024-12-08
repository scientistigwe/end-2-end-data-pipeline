import React, { useState } from "react";
import type { DBSourceConfig } from "../../types/dataSources";
import { Card, CardHeader, CardContent } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Textarea } from "../../../components/ui/textarea";

interface DatabasePreviewProps {
  source: DBSourceConfig;
  onExecuteQuery: (query: string) => void;
  className?: string;
}

export const DatabasePreview: React.FC<DatabasePreviewProps> = ({
  onExecuteQuery,
  className = "",
}) => {
  const [query, setQuery] = useState("");

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="font-medium">Database Query</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">SQL Query</label>
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter SQL query..."
              rows={4}
              className="font-mono"
            />
          </div>
          <Button
            onClick={() => onExecuteQuery(query)}
            disabled={!query.trim()}
          >
            Execute Query
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
