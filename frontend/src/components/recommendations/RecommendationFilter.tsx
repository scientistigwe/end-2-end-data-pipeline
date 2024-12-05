// src/components/recommendations/RecommendationsFilters.tsx
import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import type { RecommendationFilters } from "../../types/recommendations";

interface RecommendationsFiltersProps {
  filters: RecommendationFilters;
  onChange: (filters: RecommendationFilters) => void;
  className?: string;
}

export const RecommendationsFilters: React.FC<RecommendationsFiltersProps> = ({
  filters,
  onChange,
  className = "",
}) => {
  const types = ["quality", "performance", "security", "optimization"];
  const impacts = ["high", "medium", "low"];
  const statuses = ["pending", "applied", "dismissed", "failed"];

  return (
    <Card className={className}>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium">Types</label>
          <Select
            multiple
            value={filters.types}
            onChange={(e) => onChange({ ...filters, types: e.target.value })}
          >
            {types.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium">Impact</label>
          <Select
            multiple
            value={filters.impact}
            onChange={(e) => onChange({ ...filters, impact: e.target.value })}
          >
            {impacts.map((impact) => (
              <option key={impact} value={impact}>
                {impact.charAt(0).toUpperCase() + impact.slice(1)}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium">Status</label>
          <Select
            multiple
            value={filters.status}
            onChange={(e) => onChange({ ...filters, status: e.target.value })}
          >
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium">
            Minimum Confidence: {filters.minConfidence ?? 0}%
          </label>
          <Slider
            value={[filters.minConfidence ?? 0]}
            min={0}
            max={100}
            step={5}
            onValueChange={([value]) =>
              onChange({ ...filters, minConfidence: value })
            }
          />
        </div>
      </CardContent>
    </Card>
  );
};
