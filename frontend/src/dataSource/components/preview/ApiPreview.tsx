// src/components/dataSource/preview/ApiPreview.tsx
import React, { useState } from "react";
import type { ApiSourceConfig } from "../../types/dataSources";
import { Card, CardHeader, CardContent } from "@/common/components/ui/card";
import { Button } from "@/common/components/ui/button";
import { Textarea } from "@/common/components/ui/textarea";
import { Select } from "@/common/components/ui/inputs/select";

interface ApiPreviewProps {
  source: ApiSourceConfig;
  onTestEndpoint: (config: {
    method: string;
    headers: Record<string, string>;
    body?: any;
  }) => void;
  className?: string;
}

export const ApiPreview: React.FC<ApiPreviewProps> = ({
  source,
  onTestEndpoint,
  className = "",
}) => {
  const [method, setMethod] = useState(source.config.method);
  const [headers, setHeaders] = useState(
    JSON.stringify(source.config.headers || {}, null, 2)
  );
  const [body, setBody] = useState(
    JSON.stringify(source.config.body || {}, null, 2)
  );

  const handleTest = () => {
    try {
      onTestEndpoint({
        method,
        headers: JSON.parse(headers),
        body: method !== "GET" ? JSON.parse(body) : undefined,
      });
    } catch (error) {
      console.error("Invalid JSON in headers or body");
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="font-medium">API Endpoint Test</h3>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Endpoint URL</label>
            <div className="p-2 bg-gray-50 rounded border">
              {source.config.url}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Method</label>
            <Select
              value={method}
              onChange={(e) => setMethod(e.target.value as typeof method)}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Headers (JSON)</label>
            <Textarea
              value={headers}
              onChange={(e) => setHeaders(e.target.value)}
              placeholder="Enter headers as JSON..."
              rows={3}
              className="font-mono"
            />
          </div>

          {method !== "GET" && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Request Body (JSON)</label>
              <Textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Enter request body as JSON..."
                rows={4}
                className="font-mono"
              />
            </div>
          )}

          <Button onClick={handleTest}>Test Endpoint</Button>
        </div>
      </CardContent>
    </Card>
  );
};
