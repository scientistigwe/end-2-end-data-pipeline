import React from "react";
import { Card } from "../../common/components/ui/card";
import { Input } from "../../common/components/ui/inputs/input";
import { Select } from "../../common/components/ui/inputs/select";
import { Button } from "../../common/components/ui/button/Button";
import { X } from "lucide-react";
import { DecisionFilters as IDecisionFilters } from "../types/decisions";

interface DecisionFiltersProps {
  filters: IDecisionFilters;
  onFilterChange: (filters: IDecisionFilters) => void;
  onReset: () => void;
  className?: string;
}

export const DecisionFilters: React.FC<DecisionFiltersProps> = ({
  filters,
  onFilterChange,
  onReset,
  className = "",
}) => {
  const handleMultiSelect =
    (key: keyof IDecisionFilters) =>
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const options = Array.from(e.target.selectedOptions);
      onFilterChange({
        ...filters,
        [key]: options.map((opt) => opt.value),
      });
    };

  const handleDateChange =
    (key: "start" | "end") => (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      onFilterChange({
        ...filters,
        dateRange: {
          start: key === "start" ? value : filters.dateRange?.start || "",
          end: key === "end" ? value : filters.dateRange?.end || "",
        },
      });
    };

  return (
    <Card className={`p-4 ${className}`}>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-medium">Filters</h3>
          <Button variant="ghost" size="sm" onClick={onReset}>
            <X className="h-4 w-4 mr-1" />
            Reset
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm">Type</label>
            <Select
              multiple
              value={filters.types || []}
              onChange={handleMultiSelect("types")}
            >
              <option value="quality">Quality</option>
              <option value="pipeline">Pipeline</option>
              <option value="security">Security</option>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm">Status</label>
            <Select
              multiple
              value={filters.status || []}
              onChange={handleMultiSelect("status")}
            >
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
              <option value="deferred">Deferred</option>
              <option value="expired">Expired</option>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm">Urgency</label>
            <Select
              multiple
              value={filters.urgency || []}
              onChange={handleMultiSelect("urgency")}
            >
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm">Assigned To</label>
            <Select
              multiple
              value={filters.assignedTo || []}
              onChange={handleMultiSelect("assignedTo")}
            >
              {(filters.assignedTo || []).map((user) => (
                <option key={user} value={user}>
                  {user}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm">Date From</label>
            <Input
              type="date"
              value={filters.dateRange?.start || ""}
              onChange={handleDateChange("start")}
              required
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm">Date To</label>
            <Input
              type="date"
              value={filters.dateRange?.end || ""}
              onChange={handleDateChange("end")}
              required
            />
          </div>
        </div>
      </div>
    </Card>
  );
};
