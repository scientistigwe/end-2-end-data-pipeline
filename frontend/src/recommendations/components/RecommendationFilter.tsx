import React from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/common/components/ui/card";
import { Select } from "@/common/components/ui/inputs/select";
import { Slider } from "@/common/components/ui/slider";
import { Badge } from "@/common/components/ui/badge";
import { Button } from "@/common/components/ui/button";
import { X } from "lucide-react";
import {
  RECOMMENDATION_TYPES,
  RECOMMENDATION_STATUSES,
  RECOMMENDATION_TYPE_LABELS,
  RECOMMENDATION_STATUS_LABELS,
  RECOMMENDATION_CONFIG,
} from "../constants";
import { IMPACT_LEVELS, IMPACT_LEVEL_LABELS } from "@/common/types/common";
import type { RecommendationFilters as FilterType } from "../types/events";

interface RecommendationFiltersProps {
  filters: FilterType;
  onChange: (filters: FilterType) => void;
  onReset?: () => void;
  className?: string;
}

export const RecommendationFilters: React.FC<RecommendationFiltersProps> = ({
  filters,
  onChange,
  onReset,
  className = "",
}) => {
  const handleMultiSelect =
    (field: keyof Pick<FilterType, "types" | "impact" | "status">) =>
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const options = Array.from(e.target.selectedOptions);
      onChange({
        ...filters,
        [field]: options.map((option) => option.value),
      });
    };

  const getSelectedCount = (): number => {
    return (
      (filters.types?.length ?? 0) +
      (filters.impact?.length ?? 0) +
      (filters.status?.length ?? 0) +
      (filters.minConfidence ? 1 : 0)
    );
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Filters</CardTitle>
        {getSelectedCount() > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="h-8 px-2 lg:px-3"
          >
            Reset
            <X className="ml-2 h-4 w-4" />
          </Button>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Type Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Types</label>
          <Select
            multiple
            value={filters.types ?? []}
            onChange={handleMultiSelect("types")}
            className="min-h-[40px]"
          >
            {RECOMMENDATION_TYPES.map((type) => (
              <option key={type} value={type}>
                {RECOMMENDATION_TYPE_LABELS[type]}
              </option>
            ))}
          </Select>
          {filters.types && filters.types.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {filters.types.map((type) => (
                <Badge key={type} variant="secondary" className="text-xs">
                  {RECOMMENDATION_TYPE_LABELS[type]}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Impact Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Impact Level</label>
          <Select
            multiple
            value={filters.impact ?? []}
            onChange={handleMultiSelect("impact")}
            className="min-h-[40px]"
          >
            {IMPACT_LEVELS.map((impact) => (
              <option key={impact} value={impact}>
                {IMPACT_LEVEL_LABELS[impact]}
              </option>
            ))}
          </Select>
          {filters.impact && filters.impact.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {filters.impact.map((impact) => (
                <Badge key={impact} variant="secondary" className="text-xs">
                  {IMPACT_LEVEL_LABELS[impact]}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Status Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Status</label>
          <Select
            multiple
            value={filters.status ?? []}
            onChange={handleMultiSelect("status")}
            className="min-h-[40px]"
          >
            {RECOMMENDATION_STATUSES.map((status) => (
              <option key={status} value={status}>
                {RECOMMENDATION_STATUS_LABELS[status]}
              </option>
            ))}
          </Select>
          {filters.status && filters.status.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {filters.status.map((status) => (
                <Badge key={status} variant="secondary" className="text-xs">
                  {RECOMMENDATION_STATUS_LABELS[status]}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Confidence Filter */}
        <div className="space-y-2">
          <div className="flex justify-between">
            <label className="text-sm font-medium">Minimum Confidence</label>
            <span className="text-sm text-muted-foreground">
              {filters.minConfidence ?? RECOMMENDATION_CONFIG.MIN_CONFIDENCE}%
            </span>
          </div>
          <Slider
            value={[
              filters.minConfidence ?? RECOMMENDATION_CONFIG.MIN_CONFIDENCE,
            ]}
            min={RECOMMENDATION_CONFIG.MIN_CONFIDENCE}
            max={RECOMMENDATION_CONFIG.MAX_CONFIDENCE}
            step={5}
            onValueChange={([value]) =>
              onChange({ ...filters, minConfidence: value })
            }
            className="py-2"
          />
        </div>
      </CardContent>
    </Card>
  );
};
