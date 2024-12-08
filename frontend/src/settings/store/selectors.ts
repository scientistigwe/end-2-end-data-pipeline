import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/store';

export const selectSettings = (state: RootState) => state.settings.settings;
export const selectSettingsLoading = (state: RootState) => state.settings.isLoading;
export const selectSettingsError = (state: RootState) => state.settings.error;
