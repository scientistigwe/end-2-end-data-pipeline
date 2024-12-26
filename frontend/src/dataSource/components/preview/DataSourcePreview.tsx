// src/dataSource/components/preview/DataSourcePreview.tsx
import React from "react";
import { Card } from "@/common/components/ui/card";
import { Table } from "@/common/components/ui/table/Table";

import type { PreviewData } from "../../types/base";

interface DataSourcePreviewProps {
  data: PreviewData;
  className?: string;
}

export const DataSourcePreview: React.FC<DataSourcePreviewProps> = ({
  data,
  className = "",
}) => {
  return (
    <Card className={className}>
      <div className="p-4">
        <h3 className="text-lg font-medium mb-4">Data Preview</h3>
        <Table>
          <thead>
            <tr>
              {data.fields.map((field) => (
                <th key={field.name}>{field.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.data.map((row, i) => (
              <tr key={i}>
                {data.fields.map((field) => (
                  <td key={field.name}>{String(row[field.name])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </Table>
        <div className="mt-2 text-sm text-gray-500">
          Showing {data.data.length} of {data.totalRows} rows
        </div>
      </div>
    </Card>
  );
};
