// src/components/decisions/DecisionStats.tsx
import React from "react";
import { Card } from "../../common/components/ui/card";
import { Progress } from "../../common/components/ui/progress";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import type { Decision } from "../types/decisions";

interface DecisionStats {
  total: number;
  byStatus: Record<string, number>;
  byType: Record<string, number>;
  byUrgency: Record<string, number>;
  averageTimeToDecision: number;
  trendsData: Array<{
    date: string;
    count: number;
  }>;
}

interface DecisionStatsProps {
  decisions: Decision[];
  className?: string;
}

export const DecisionStats: React.FC<DecisionStatsProps> = ({
  decisions,
  className = "",
}) => {
  const calculateStats = (): DecisionStats => {
    const stats: DecisionStats = {
      total: decisions.length,
      byStatus: {},
      byType: {},
      byUrgency: {},
      averageTimeToDecision: 0,
      trendsData: [],
    };

    decisions.forEach((decision) => {
      // Count by status
      stats.byStatus[decision.status] =
        (stats.byStatus[decision.status] || 0) + 1;

      // Count by type
      stats.byType[decision.type] = (stats.byType[decision.type] || 0) + 1;

      // Count by urgency
      stats.byUrgency[decision.urgency] =
        (stats.byUrgency[decision.urgency] || 0) + 1;

      // Calculate average time to decision
      if (decision.status === "completed" && decision.updatedAt) {
        const timeToDecision =
          new Date(decision.updatedAt).getTime() -
          new Date(decision.createdAt).getTime();
        stats.averageTimeToDecision += timeToDecision;
      }
    });

    if (stats.total > 0) {
      stats.averageTimeToDecision /= stats.total;
    }

    // Generate trends data
    const dates = decisions.map((d) => d.createdAt.split("T")[0]);
    const uniqueDates = [...new Set(dates)].sort();
    stats.trendsData = uniqueDates.map((date) => ({
      date,
      count: dates.filter((d) => d === date).length,
    }));

    return stats;
  };

  const stats = calculateStats();
  const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042"];

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${className}`}>
      <Card className="p-4">
        <h3 className="font-medium mb-4">Decision Status Distribution</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={Object.entries(stats.byStatus).map(([name, value]) => ({
                name,
                value,
              }))}
              innerRadius={60}
              outerRadius={80}
              paddingAngle={5}
              dataKey="value"
            >
              {Object.entries(stats.byStatus).map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </Card>

      <Card className="p-4">
        <h3 className="font-medium mb-4">Decision Trends</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={stats.trendsData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#8884d8" />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card className="p-4">
        <h3 className="font-medium mb-4">Decision Types</h3>
        <div className="space-y-4">
          {Object.entries(stats.byType).map(([type, count]) => (
            <div key={type}>
              <div className="flex justify-between text-sm mb-1">
                <span>{type}</span>
                <span>{((count / stats.total) * 100).toFixed(1)}%</span>
              </div>
              <Progress value={(count / stats.total) * 100} />
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h3 className="font-medium mb-4">Key Metrics</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">Total Decisions</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">Pending Decisions</p>
            <p className="text-2xl font-bold">{stats.byStatus.pending || 0}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">Avg. Time to Decision</p>
            <p className="text-2xl font-bold">
              {(stats.averageTimeToDecision / (1000 * 60 * 60)).toFixed(1)}h
            </p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">High Urgency</p>
            <p className="text-2xl font-bold">{stats.byUrgency.high || 0}</p>
          </div>
        </div>
      </Card>
    </div>
  );
};
