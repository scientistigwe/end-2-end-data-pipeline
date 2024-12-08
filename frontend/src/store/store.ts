// src/store/store.ts
import { configureStore } from '@reduxjs/toolkit';
import authReducer from '@/auth/store/authSlice';
import analysisReducer from '@/analysis/store/analysisSlice';
import dataSourceReducer from '@/dataSource/store/dataSourceSlice';
import pipelineReducer from '@/pipeline/store/pipelineSlice';
import monitoringReducer from '@/monitoring/store/monitoringSlice';
import recommendationsReducer from '@/recommendations/store/recommendationsSlice';
import reportReducer from '@/reports/store/reportSlice';
import uiReducer from '@/common/store/ui/uiSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    analysis: analysisReducer,
    dataSources: dataSourceReducer,
    pipelines: pipelineReducer,
    monitoring: monitoringReducer,
    recommendations: recommendationsReducer,
    reports: reportReducer,
    ui: uiReducer
  }
});

export type AppDispatch = typeof store.dispatch;
export type RootState = ReturnType<typeof store.getState>;

// Optional: Create typed hooks
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;