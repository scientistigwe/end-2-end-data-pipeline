// src/pipeline/utils/pipelineUtils.ts
import type { Pipeline, PipelineStep, PipelineConfig } from '../types/pipeline';

/**
 * Pipeline Configuration Utils
 */
export function generatePipelineId(): string {
  return `pip_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function generateStepId(prefix: string = 'step'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
}

export function createDefaultPipelineConfig(): PipelineConfig {
  return {
    name: '',
    mode: 'development',
    steps: [],
    sourceId: '',
    schedule: {
      enabled: false
    },
    retryConfig: {
      maxAttempts: 3,
      backoffMultiplier: 1.5
    }
  };
}

/**
 * Pipeline Validation Utils
 */
export function validateStepDependencies(steps: PipelineStep[]): boolean {
  const stepIds = new Set(steps.map(step => step.id));
  
  // Check for circular dependencies
  const visited = new Set<string>();
  const recursionStack = new Set<string>();

  function hasCyclicDependency(stepId: string): boolean {
    if (!visited.has(stepId)) {
      visited.add(stepId);
      recursionStack.add(stepId);

      const step = steps.find(s => s.id === stepId);
      if (step?.dependencies) {
        for (const depId of step.dependencies) {
          if (!visited.has(depId) && hasCyclicDependency(depId)) {
            return true;
          } else if (recursionStack.has(depId)) {
            return true;
          }
        }
      }
    }
    recursionStack.delete(stepId);
    return false;
  }

  for (const step of steps) {
    if (step.dependencies) {
      // Check if all dependencies exist
      const invalidDeps = step.dependencies.filter(depId => !stepIds.has(depId));
      if (invalidDeps.length > 0) return false;

      // Check for circular dependencies
      if (hasCyclicDependency(step.id)) return false;
    }
  }

  return true;
}

/**
 * Pipeline Analysis Utils
 */
export function calculatePipelineProgress(pipeline: Pipeline): number {
  if (!pipeline.steps.length) return 0;
  if (pipeline.status === 'completed') return 100;
  if (pipeline.status === 'idle') return 0;

  const completedSteps = pipeline.steps.filter(step => step.status === 'completed').length;
  const runningStep = pipeline.steps.find(step => step.status === 'running');
  
  const baseProgress = (completedSteps / pipeline.steps.length) * 100;
  if (!runningStep) return baseProgress;

  // Estimate progress of running step (if available)
  const stepProgress = runningStep.progress || 0;
  const stepContribution = (1 / pipeline.steps.length) * stepProgress;

  return baseProgress + stepContribution;
}

export function estimateRemainingTime(
  pipeline: Pipeline,
  historicalRuns: { duration: number }[]
): number {
  if (pipeline.status !== 'running') return 0;

  const avgStepDuration = calculateAverageStepDuration(historicalRuns);
  const remainingSteps = pipeline.steps.filter(
    step => !['completed', 'failed'].includes(step.status)
  ).length;

  return avgStepDuration * remainingSteps;
}

function calculateAverageStepDuration(runs: { duration: number }[]): number {
  if (!runs.length) return 0;
  const totalDuration = runs.reduce((sum, run) => sum + run.duration, 0);
  return totalDuration / runs.length;
}

