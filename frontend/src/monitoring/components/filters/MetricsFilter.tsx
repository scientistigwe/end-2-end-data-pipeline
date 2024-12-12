// src/monitoring/components/filters/MetricsFilter.tsx
import React from "react";
import { Card, CardContent } from "../../../common/components/ui/card";
import { Input } from "../../../common/components/ui/inputs/input";
import { Select } from "../../../common/components/ui/inputs/select";
import { Button } from "../../../common/components/ui/button";
import { MONITORING_CONFIG } from "../../constants";

interface MetricsFilterProps {
  onFilterChange: (filters: MetricsFilterOptions) => void;
  className?: string;
}

interface MetricsFilterOptions {
  timeRange: string;
  metricTypes: string[];
  status?: string;
  search?: string;
}

export const MetricsFilter: React.FC<MetricsFilterProps> = ({
  onFilterChange,
  className = "",
}) => {
  const [filters, setFilters] = React.useState<MetricsFilterOptions>({
    timeRange: "1h",
    metricTypes: [],
    status: undefined,
    search: "",
  });

  const handleFilterChange = (key: keyof MetricsFilterOptions, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  return (
    <Card className={className}>
      <CardContent className="space-y-4 p-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Time Range</label>
            <Select
              value={filters.timeRange}
              onValueChange={(value) => handleFilterChange("timeRange", value)}
            >
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Status</label>
            <Select
              value={filters.status}
              onValueChange={(value) => handleFilterChange("status", value)}
            >
              <option value="">All</option>
              <option value="healthy">Healthy</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Search Metrics</label>
          <Input
            type="text"
            placeholder="Search metrics..."
            value={filters.search}
            onChange={(e) => handleFilterChange("search", e.target.value)}
          />
        </div>
      </CardContent>
    </Card>
  );
};
