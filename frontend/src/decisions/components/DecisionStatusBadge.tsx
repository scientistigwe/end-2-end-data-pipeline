// src/decisions/components/status/DecisionStatusBadge.tsx
import React from "react";
import { Badge } from "../../common/components/ui/badge";
import type { DecisionStatus } from "../types/base";

interface DecisionStatusBadgeProps {
  status: DecisionStatus;
  className?: string;
}

export const DecisionStatusBadge: React.FC<DecisionStatusBadgeProps> = ({
  status,
  className = "",
}) => {
  const getStatusColor = (status: DecisionStatus) => {
    switch (status) {
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "completed":
        return "bg-green-100 text-green-800";
      case "deferred":
        return "bg-blue-100 text-blue-800";
      case "expired":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <Badge className={`${getStatusColor(status)} ${className}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
};
