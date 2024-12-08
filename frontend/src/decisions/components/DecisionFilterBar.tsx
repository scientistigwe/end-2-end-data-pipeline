// src/decisions/components/filters/DecisionFilterBar.tsx
import React from "react";
import { Select } from "../../common/components/ui/inputs/select";
import { Button } from "../../common/components/ui/button";
import {
  DECISION_TYPES,
  DECISION_STATUSES,
  DECISION_URGENCIES,
} from "../constants";
import type { DecisionFilters } from "../types/decisions";

interface DecisionFilterBarProps {
  filters: DecisionFilters;
  onFilterChange: (filters: DecisionFilters) => void;
  onReset: () => void;
  className?: string;
}

export const DecisionFilterBar: React.FC<DecisionFilterBarProps> = ({
  filters,
  onFilterChange,
  onReset,
  className = "",
}) => {
  const handleChange = (field: keyof DecisionFilters, value: any) => {
    onFilterChange({
      ...filters,
      [field]: value,
    });
  };

  return (
    <div className={`flex gap-4 items-center ${className}`}>
      <Select
        value={filters.types?.[0] || ""}
        onChange={(e) => handleChange("types", [e.target.value])}
        className="w-32"
      >
        <option value="">All Types</option>
        {DECISION_TYPES.map((type) => (
          <option key={type} value={type}>
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </option>
        ))}
      </Select>

      <Select
        value={filters.status?.[0] || ""}
        onChange={(e) => handleChange("status", [e.target.value])}
        className="w-32"
      >
        <option value="">All Status</option>
        {DECISION_STATUSES.map((status) => (
          <option key={status} value={status}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </option>
        ))}
      </Select>

      <Select
        value={filters.urgency?.[0] || ""}
        onChange={(e) => handleChange("urgency", [e.target.value])}
        className="w-32"
      >
        <option value="">All Urgency</option>
        {DECISION_URGENCIES.map((urgency) => (
          <option key={urgency} value={urgency}>
            {urgency.charAt(0).toUpperCase() + urgency.slice(1)}
          </option>
        ))}
      </Select>

      <Button variant="outline" onClick={onReset}>
        Reset Filters
      </Button>
    </div>
  );
};
