// src/decisions/context/DecisionContext.tsx
import React, { createContext, useContext, useState, useCallback } from "react";
import type { Decision, DecisionFilters } from "../types/decisions";

interface DecisionContextValue {
  selectedDecision: Decision | null;
  filters: DecisionFilters;
  setSelectedDecision: (decision: Decision | null) => void;
  setFilters: (filters: DecisionFilters) => void;
  clearFilters: () => void;
}

const DecisionContext = createContext<DecisionContextValue | undefined>(
  undefined
);

export const DecisionProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(
    null
  );
  const [filters, setFilters] = useState<DecisionFilters>({});

  const clearFilters = useCallback(() => {
    setFilters({});
  }, []);

  const value = {
    selectedDecision,
    filters,
    setSelectedDecision,
    setFilters,
    clearFilters,
  };

  return (
    <DecisionContext.Provider value={value}>
      {children}
    </DecisionContext.Provider>
  );
};

export const useDecisionContext = () => {
  const context = useContext(DecisionContext);
  if (context === undefined) {
    throw new Error(
      "useDecisionContext must be used within a DecisionProvider"
    );
  }
  return context;
};
