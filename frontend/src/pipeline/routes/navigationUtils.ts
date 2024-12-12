  // src/pipeline/routes/navigationUtils.ts
  import { useNavigate } from 'react-router-dom';
  import { PIPELINE_ROUTES } from './pipelineRoutes';
  import { getPipelinePathWithId } from './utils/routeParams';
  
  export function usePipelineNavigation() {
    const navigate = useNavigate();
  
    return {
      goToDashboard: () => navigate(PIPELINE_ROUTES.DASHBOARD),
      goToPipelinesList: () => navigate(PIPELINE_ROUTES.LIST),
      goToPipelineDetails: (id: string) => 
        navigate(getPipelinePathWithId(PIPELINE_ROUTES.DETAILS, id)),
      goToPipelineRuns: (id: string) => 
        navigate(getPipelinePathWithId(PIPELINE_ROUTES.RUNS, id)),
      goToPipelineMetrics: (id: string) => 
        navigate(getPipelinePathWithId(PIPELINE_ROUTES.METRICS, id))
    };
  }
  
