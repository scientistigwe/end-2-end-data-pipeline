// src/common/store/types.ts
import type { UIState } from './ui/uiSlice';

export interface RootState {
  ui: UIState;
  // Other module states will be added by the modules themselves
}