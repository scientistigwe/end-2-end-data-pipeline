// src/store/reducers.ts
import { Reducer } from '@reduxjs/toolkit';
import authReducer from '@/auth/store/authSlice';
import analysisReducer from '@/analysis/store/analysisSlice';
import dataSourceReducer from '@/dataSource/store/dataSourceSlice';
import pipelineReducer from '@/pipeline/store/pipelineSlice';
import decisionReducer from '@/decisions/store/decisionsSlice'
import monitoringReducer from '@/monitoring/store/monitoringSlice';
import recommendationsReducer from '@/recommendations/store/recommendationsSlice';
import reportReducer from '@/reports/store/reportSlice';
import uiReducer from '@/common/store/ui/uiSlice';

// Define a type-safe reducer map
const reducers = {
  auth: authReducer as Reducer,
  analysis: analysisReducer as Reducer,
    dataSources: dataSourceReducer as Reducer,
    pipelines: pipelineReducer as Reducer,
  decisions: decisionReducer as Reducer,
  monitoring: monitoringReducer as Reducer,
  recommendations: recommendationsReducer as Reducer,
  reports: reportReducer as Reducer,
  ui: uiReducer as Reducer,
} as const;

export default reducers;
