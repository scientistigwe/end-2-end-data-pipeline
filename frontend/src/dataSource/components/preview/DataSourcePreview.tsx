// src/components/datasource/DataSourcePreview.tsx
import React, { useState } from "react";
import { Card, CardHeader, CardContent } from "../../../../components/ui/card";
import { Input } from "../../../../components/ui/input";
import { Select } from "../../../../components/ui/select";
import { Badge } from "../../../../components/ui/badge";
import { Button } from "../../../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../../components/ui/table";
import type { PreviewData } from "../../types/dataSources";
import { RefreshCw } from "lucide-react";

interface DataSourcePreviewProps {
  preview: PreviewData;
  onRefresh?: () => void;
  onLoadMore?: () => void;
  className?: string;
}

// Helper function to format cell values based on type
function formatCellValue(value: unknown, type: string): string {
  if (value === null || value === undefined) {
    return "-";
  }

  switch (type.toLowerCase()) {
    case "date":
    case "datetime":
      return new Date(value as string).toLocaleString();
    case "boolean":
      return value ? "Yes" : "No";
    case "number":
    case "float":
    case "integer":
      return typeof value === "number" ? value.toLocaleString() : String(value);
    case "json":
    case "object":
      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    default:
      return String(value);
  }
}

export const DataSourcePreview: React.FC<DataSourcePreviewProps> = ({
  preview,
  onRefresh,
  onLoadMore,
  className = "",
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedField, setSelectedField] = useState<string>("");

  const filteredData = preview.data.filter((row) => {
    if (!searchTerm || !selectedField) return true;
    const value = String(row[selectedField]).toLowerCase();
    return value.includes(searchTerm.toLowerCase());
  });

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex justify-between items-center">
          <h3 className="font-medium">Data Preview</h3>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Select
                value={selectedField}
                onChange={(e) => setSelectedField(e.target.value)}
              >
                <option value="">Select field...</option>
                {preview.fields.map((field) => (
                  <option key={field.name} value={field.name}>
                    {field.name}
                  </option>
                ))}
              </Select>
              <Input
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-64"
              />
            </div>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="border rounded-md">
          <Table>
            // src/components/datasource/DataSourcePreview.tsx (continued)
            <TableHeader>
              <TableRow>
                {preview.fields.map((field) => (
                  <TableHead key={field.name}>
                    <div className="flex items-center space-x-2">
                      <span>{field.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {field.type}
                      </Badge>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredData.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={preview.fields.length}
                    className="text-center py-8"
                  >
                    No data found
                  </TableCell>
                </TableRow>
              ) : (
                filteredData.map((row, rowIndex) => (
                  <TableRow key={rowIndex}>
                    {preview.fields.map((field) => (
                      <TableCell key={field.name}>
                        {formatCellValue(row[field.name], field.type)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <div className="mt-4 text-sm text-gray-500 flex justify-between items-center">
          <span>
            Showing {filteredData.length} of {preview.totalRows} rows
          </span>
          {preview.totalRows > filteredData.length && onLoadMore && (
            <Button variant="outline" size="sm" onClick={onLoadMore}>
              Load More
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
