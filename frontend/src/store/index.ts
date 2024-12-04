// src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import { useDispatch, useSelector, TypedUseSelectorHook } from 'react-redux';
import dataSourcesReducer from './slices/dataSourceSlice';
import pipelineReducer from './slices/pipelineSlice';
import analysisReducer from './slices/analysisSlice';
import monitoringReducer from './slices/monitoringSlice';
import recommendationsReducer from './slices/recommendationSlice';
import reportsReducer from './slices/reportSlice';
import uiReducer from './slices/uiSlice';
import authReducer from './slices/authSlice';

export const store = configureStore({
  reducer: {
    dataSources: dataSourcesReducer,
    pipelines: pipelineReducer,
    analysis: analysisReducer,
    monitoring: monitoringReducer,
    recommendations: recommendationsReducer,
    reports: reportsReducer,
    ui: uiReducer,
    auth: authReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['auth/setCredentials'],
        ignoredActionPaths: ['payload.timestamp'],
        ignoredPaths: ['items.dates']
      }
    }),
  devTools: process.env.NODE_ENV !== 'production'
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Use throughout your app instead of plain `useDispatch` and `useSelector`
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;