// src/pipeline/services/pipelineService.ts
import type {
    Pipeline,
    PipelineConfig,
    PipelineStep,
    PipelineRun,
    PipelineMetrics,
    PipelineStatus
  } from '../types/metrics';
  import { pipelineApi } from '../api/pipelineApi';
  import { PIPELINE_CONSTANTS } from '../constants';
  
  export class PipelineService {
    /**
     * Pipeline Configuration Validation
     */
    async validatePipelineConfig(config: PipelineConfig): Promise<{
      isValid: boolean;
      errors: string[];
    }> {
      const errors: string[] = [];
  
      // Validate name
      if (!config.name || config.name.length < PIPELINE_CONSTANTS.VALIDATION.NAME_MIN_LENGTH) {
        errors.push(`Name must be at least ${PIPELINE_CONSTANTS.VALIDATION.NAME_MIN_LENGTH} characters`);
      }
  
      if (config.name.length > PIPELINE_CONSTANTS.VALIDATION.NAME_MAX_LENGTH) {
        errors.push(`Name must not exceed ${PIPELINE_CONSTANTS.VALIDATION.NAME_MAX_LENGTH} characters`);
      }
  
      // Validate steps
      if (!config.steps || config.steps.length === 0) {
        errors.push('Pipeline must have at least one step');
      } else {
        for (const step of config.steps) {
          if (!this.validatePipelineStep(step)) {
            errors.push(`Invalid step configuration: ${step.name}`);
          }
        }
      }
  
      // Validate dependencies
      const stepIds = new Set(config.steps.map(step => step.id));
      for (const step of config.steps) {
        if (step.dependencies) {
          for (const depId of step.dependencies) {
            if (!stepIds.has(depId)) {
              errors.push(`Step ${step.name} has invalid dependency: ${depId}`);
            }
          }
        }
      }
  
      return {
        isValid: errors.length === 0,
        errors
      };
    }
  
    private validatePipelineStep(step: PipelineStep): boolean {
      return (
        !!step.name &&
        !!step.type &&
        Object.values(PIPELINE_CONSTANTS.STEPS.TYPES).includes(step.type)
      );
    }
  
    /**
     * Pipeline Execution Analysis
     */
    analyzePipelinePerformance(runs: PipelineRun[]): {
      successRate: number;
      averageDuration: number;
      failurePoints: string[];
      recommendations: string[];
    } {
      const totalRuns = runs.length;
      const successfulRuns = runs.filter(run => run.status === 'completed').length;
      
      // Calculate metrics
      const successRate = (successfulRuns / totalRuns) * 100;
      const averageDuration = runs.reduce((acc, run) => acc + (run.duration || 0), 0) / totalRuns;
  
      // Analyze failure points
      const failurePoints = this.analyzeFailurePoints(runs);
      
      // Generate recommendations
      const recommendations = this.generateRecommendations(runs, failurePoints);
  
      return {
        successRate,
        averageDuration,
        failurePoints,
        recommendations
      };
    }
  
    private analyzeFailurePoints(runs: PipelineRun[]): string[] {
      const failurePoints: Record<string, number> = {};
  
      runs.forEach(run => {
        if (run.status === 'failed' && run.error?.step) {
          failurePoints[run.error.step] = (failurePoints[run.error.step] || 0) + 1;
        }
      });
  
      return Object.entries(failurePoints)
        .sort(([, a], [, b]) => b - a)
        .map(([step]) => step);
    }
  
    private generateRecommendations(runs: PipelineRun[], failurePoints: string[]): string[] {
      const recommendations: string[] = [];
  
      // Analyze step durations
      const stepDurations = this.analyzeStepDurations(runs);
      for (const [step, duration] of Object.entries(stepDurations)) {
        if (duration > PIPELINE_CONSTANTS.STEPS.DEFAULT_TIMEOUT) {
          recommendations.push(`Consider optimizing step "${step}" - average duration exceeds timeout`);
        }
      }
  
      // Analyze failure patterns
      failurePoints.forEach(step => {
        recommendations.push(`Review error handling in step "${step}" - frequent failures detected`);
      });
  
      return recommendations;
    }
  
    private analyzeStepDurations(runs: PipelineRun[]): Record<string, number> {
      const stepDurations: Record<string, { total: number; count: number }> = {};
  
      runs.forEach(run => {
        run.steps.forEach(step => {
          if (!stepDurations[step.stepId]) {
            stepDurations[step.stepId] = { total: 0, count: 0 };
          }
          if (step.duration) {
            stepDurations[step.stepId].total += step.duration;
            stepDurations[step.stepId].count += 1;
          }
        });
      });
  
      return Object.entries(stepDurations).reduce((acc, [step, { total, count }]) => {
        acc[step] = total / count;
        return acc;
      }, {} as Record<string, number>);
    }
  
    /**
     * Pipeline Metrics Processing
     */
    processMetrics(metrics: PipelineMetrics[]): {
      throughput: number;
      latency: number;
      errorRate: number;
      resourceUtilization: {
        cpu: number;
        memory: number;
      };
      trends: {
        throughputTrend: number;
        latencyTrend: number;
        errorRateTrend: number;
      };
    } {
      // Calculate current values
      const latest = metrics[metrics.length - 1]?.metrics || {
        throughput: 0,
        latency: 0,
        errorRate: 0,
        resourceUsage: { cpu: 0, memory: 0 }
      };
  
      // Calculate trends
      const pastPeriod = metrics.slice(-6); // Last 5 minutes (assuming 1-minute intervals)
      const trends = this.calculateMetricTrends(pastPeriod);
  
      return {
        throughput: latest.throughput,
        latency: latest.latency,
        errorRate: latest.errorRate,
        resourceUtilization: {
          cpu: latest.resourceUsage.cpu,
          memory: latest.resourceUsage.memory
        },
        trends
      };
    }
  
    private calculateMetricTrends(metrics: PipelineMetrics[]): {
      throughputTrend: number;
      latencyTrend: number;
      errorRateTrend: number;
    } {
      if (metrics.length < 2) {
        return { throughputTrend: 0, latencyTrend: 0, errorRateTrend: 0 };
      }
  
      const first = metrics[0].metrics;
      const last = metrics[metrics.length - 1].metrics;
  
      return {
        throughputTrend: ((last.throughput - first.throughput) / first.throughput) * 100,
        latencyTrend: ((last.latency - first.latency) / first.latency) * 100,
        errorRateTrend: ((last.errorRate - first.errorRate) / first.errorRate) * 100
      };
    }
  
    /**
     * Pipeline Status Management
     */
    getStatusSeverity(status: PipelineStatus): number {
      const severityMap: Record<PipelineStatus, number> = {
        'failed': 3,
        'error': 3,
        'running': 2,
        'paused': 2,
        'completed': 1,
        'idle': 0,
        'cancelled': 0
      };
  
      return severityMap[status] || 0;
    }
  
    shouldAlertStatus(status: PipelineStatus, metrics: PipelineMetrics): boolean {
      return (
        this.getStatusSeverity(status) === 3 ||
        metrics.metrics.errorRate > 0.1 ||
        metrics.metrics.latency > PIPELINE_CONSTANTS.STEPS.DEFAULT_TIMEOUT
      );
    }
  }
  
