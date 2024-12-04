// store/slices/recommendationsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Define types
type Priority = 'high' | 'medium' | 'low';
type RecommendationStatus = 'pending' | 'applied' | 'dismissed' | 'in_progress';
type RecommendationType = 'performance' | 'security' | 'cost' | 'quality' | 'other';
type ImpactArea = 'pipeline' | 'datasource' | 'system' | 'analysis';

// Define interfaces
interface RecommendationDetails {
  title: string;
  description: string;
  impact: string;
  effort: 'low' | 'medium' | 'high';
  benefits: string[];
  risks?: string[];
  suggestedActions: string[];
  relatedResources?: {
    id: string;
    type: string;
    name: string;
  }[];
}

interface Recommendation {
  id: string;
  type: RecommendationType;
  priority: Priority;
  status: RecommendationStatus;
  details: RecommendationDetails;
  impactArea: ImpactArea;
  createdAt: string;
  updatedAt: string;
  appliedAt?: string;
  dismissedAt?: string;
  dismissReason?: string;
  implementationNotes?: string;
}

interface RecommendationState {
  recommendations: Record<string, Recommendation>;
  appliedRecommendations: string[];
  dismissedRecommendations: string[];
  loading: boolean;
  error: string | null;
  filters: {
    priority?: Priority[];
    status?: RecommendationStatus[];
    type?: RecommendationType[];
  };
}

// Define payload interfaces
interface AddRecommendationPayload {
  id: string;
  type: RecommendationType;
  priority: Priority;
  details: RecommendationDetails;
  impactArea: ImpactArea;
}

interface UpdateRecommendationPayload {
  id: string;
  updates: Partial<Recommendation>;
}

interface DismissRecommendationPayload {
  id: string;
  reason: string;
}

interface ApplyRecommendationPayload {
  id: string;
  implementationNotes?: string;
}

const initialState: RecommendationState = {
  recommendations: {},
  appliedRecommendations: [],
  dismissedRecommendations: [],
  loading: false,
  error: null,
  filters: {}
};

export const recommendationsSlice = createSlice({
  name: 'recommendations',
  initialState,
  reducers: {
    addRecommendation(state, action: PayloadAction<AddRecommendationPayload>) {
      const timestamp = new Date().toISOString();
      state.recommendations[action.payload.id] = {
        ...action.payload,
        status: 'pending',
        createdAt: timestamp,
        updatedAt: timestamp
      };
    },

    updateRecommendation(state, action: PayloadAction<UpdateRecommendationPayload>) {
      const recommendation = state.recommendations[action.payload.id];
      if (recommendation) {
        state.recommendations[action.payload.id] = {
          ...recommendation,
          ...action.payload.updates,
          updatedAt: new Date().toISOString()
        };
      }
    },

    applyRecommendation(state, action: PayloadAction<ApplyRecommendationPayload>) {
      const recommendation = state.recommendations[action.payload.id];
      if (recommendation) {
        const timestamp = new Date().toISOString();
        recommendation.status = 'applied';
        recommendation.appliedAt = timestamp;
        recommendation.updatedAt = timestamp;
        recommendation.implementationNotes = action.payload.implementationNotes;
        
        if (!state.appliedRecommendations.includes(action.payload.id)) {
          state.appliedRecommendations.push(action.payload.id);
        }
      }
    },

    dismissRecommendation(state, action: PayloadAction<DismissRecommendationPayload>) {
      const recommendation = state.recommendations[action.payload.id];
      if (recommendation) {
        const timestamp = new Date().toISOString();
        recommendation.status = 'dismissed';
        recommendation.dismissedAt = timestamp;
        recommendation.dismissReason = action.payload.reason;
        recommendation.updatedAt = timestamp;

        if (!state.dismissedRecommendations.includes(action.payload.id)) {
          state.dismissedRecommendations.push(action.payload.id);
        }
      }
    },

    setFilters(state, action: PayloadAction<RecommendationState['filters']>) {
      state.filters = action.payload;
    },

    clearFilters(state) {
      state.filters = {};
    }
  }
});

// Export actions
export const {
  addRecommendation,
  updateRecommendation,
  applyRecommendation,
  dismissRecommendation,
  setFilters,
  clearFilters
} = recommendationsSlice.actions;

// Selectors
export const selectAllRecommendations = (state: RootState) => 
  Object.values(state.recommendations.recommendations);

export const selectFilteredRecommendations = (state: RootState) => {
  const recommendations = Object.values(state.recommendations.recommendations);
  const filters = state.recommendations.filters;

  return recommendations.filter(rec => {
    const matchesPriority = !filters.priority?.length || 
      filters.priority.includes(rec.priority);
    const matchesStatus = !filters.status?.length || 
      filters.status.includes(rec.status);
    const matchesType = !filters.type?.length || 
      filters.type.includes(rec.type);
    
    return matchesPriority && matchesStatus && matchesType;
  });
};

export const selectRecommendationsByPriority = (priority: Priority) => (state: RootState) =>
  Object.values(state.recommendations.recommendations).filter(rec => rec.priority === priority);

export const selectRecommendationById = (id: string) => (state: RootState) =>
  state.recommendations.recommendations[id];

export default recommendationsSlice.reducer;