// src/pipeline/api/validation.ts
import { z } from "zod";

// Helper schema for pipeline step configuration
const pipelineStepSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1, "Step name is required"),
  type: z.string().min(1, "Step type is required"),
  status: z.enum(["idle", "running", "paused", "completed", "failed", "cancelled"]).default("idle"),
  config: z.record(z.unknown()).default({}),
  dependencies: z.array(z.string()).optional(),
  enabled: z.boolean().default(true),
  timeout: z.number().positive().optional(),
  retryAttempts: z.number().min(0).optional(),
  condition: z.string().optional(),
  onFailure: z.enum(["stop", "continue", "retry"]).optional(),
  metadata: z.record(z.unknown()).optional()
});

// Main pipeline configuration validation
export const validatePipelineConfig = z.object({
  name: z.string()
    .min(1, "Pipeline name is required")
    .max(100, "Pipeline name cannot exceed 100 characters")
    .refine(name => /^[a-zA-Z0-9-_\s]+$/.test(name), {
      message: "Pipeline name can only contain letters, numbers, spaces, hyphens, and underscores"
    }),
  description: z.string().max(500).optional(),
  mode: z.enum(["development", "staging", "production"]).default("development"),
  steps: z.array(pipelineStepSchema).min(1, "At least one step is required"),
  sourceId: z.string().min(1, "Source ID is required"),
  targetId: z.string().optional(),
  schedule: z.object({
    enabled: z.boolean(),
    cron: z.string().optional(),
    timezone: z.string().optional()
  }).optional(),
  retryConfig: z.object({
    maxAttempts: z.number().min(1),
    backoffMultiplier: z.number().min(1)
  }).optional(),
  tags: z.array(z.string()).optional(),
  metadata: z.record(z.unknown()).optional()
});

// Export type for use in components and services
export type ValidPipelineConfig = z.infer<typeof validatePipelineConfig>;