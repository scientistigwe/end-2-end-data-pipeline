#!/bin/bash

# Function to create a module structure
create_module() {
    local MODULE_NAME=$1
    local MODULE_DIR="src/${MODULE_NAME}"

    # Create main directories
    mkdir -p "${MODULE_DIR}"/{__tests__/{unit/{hooks,utils},integration,e2e},api,components,context,hooks,pages,providers,routes,services,store,types,utils}

    # Create basic test files
    touch "${MODULE_DIR}"/__tests__/unit/hooks/use${MODULE_NAME^}.test.ts
    touch "${MODULE_DIR}"/__tests__/unit/utils/${MODULE_NAME}Utils.test.ts
    touch "${MODULE_DIR}"/__tests__/integration/${MODULE_NAME^}Workflow.test.tsx
    touch "${MODULE_DIR}"/__tests__/e2e/${MODULE_NAME}.cy.ts

    # Create API files
    touch "${MODULE_DIR}"/api/{client,config,${MODULE_NAME}Api,index}.ts

    # Create store files
    touch "${MODULE_DIR}"/store/{${MODULE_NAME}Slice,selectors,index}.ts

    # Create type files
    touch "${MODULE_DIR}"/types/${MODULE_NAME}.ts
    touch "${MODULE_DIR}"/types/index.ts

    # Create route files
    touch "${MODULE_DIR}"/routes/{${MODULE_NAME}Routes,index}.ts

    # Create service files
    touch "${MODULE_DIR}"/services/${MODULE_NAME}Service.ts
    touch "${MODULE_DIR}"/services/index.ts

    # Create context and provider files
    touch "${MODULE_DIR}"/context/${MODULE_NAME^}Context.tsx
    touch "${MODULE_DIR}"/context/index.ts
    touch "${MODULE_DIR}"/providers/${MODULE_NAME^}Provider.tsx
    touch "${MODULE_DIR}"/providers/index.ts

    # Create utils files
    touch "${MODULE_DIR}"/utils/${MODULE_NAME}Utils.ts
    touch "${MODULE_DIR}"/utils/formatters.ts
    touch "${MODULE_DIR}"/utils/index.ts

    # Create constants file
    touch "${MODULE_DIR}"/constants.ts
    touch "${MODULE_DIR}"/index.ts

    # Module specific components based on current structure
    case $MODULE_NAME in
        "analysis")
            touch "${MODULE_DIR}"/pages/{AnalysisPage,DashboardPage}.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            mkdir -p "${MODULE_DIR}"/components/{forms,status,reports}
            touch "${MODULE_DIR}"/components/forms/AnalysisForm.tsx
            touch "${MODULE_DIR}"/components/status/{AnalysisStatus,QualityStatus}.tsx
            touch "${MODULE_DIR}"/components/reports/{InsightReport,QualityReport}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/{useAnalysis,useAnalysisDetails,index}.ts
            ;;
        "auth")
            mkdir -p "${MODULE_DIR}"/components/admin
            touch "${MODULE_DIR}"/pages/{LoginPage,ForgotPasswordPage,RegisterPage}.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            touch "${MODULE_DIR}"/components/{AuthLayout,ChangePasswordModal,EmailVerification,ForgotPasswordForm,LoginForm,PermissionGuard,ProtectedRoute,RegisterForm,UserProfile}.tsx
            touch "${MODULE_DIR}"/components/admin/{UserForm,UserManagement}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/{useAuth,usePermissions,useSession,index}.ts
            ;;
        "dataSource")
            mkdir -p "${MODULE_DIR}"/components/{fields,forms,preview}
            touch "${MODULE_DIR}"/pages/DataSourcesPage.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            touch "${MODULE_DIR}"/components/{ApiSourceCard,DataSourceForm,DataSourceList,DataSourcePreview,DataSourceValidation,DBSourceCard,FileSourceCard,S3SourceCard,StreamSourceCard}.tsx
            touch "${MODULE_DIR}"/components/fields/{ApiFields,DBFields,FileFields,S3Fields,StreamFields,index}.tsx
            touch "${MODULE_DIR}"/components/forms/{ApiSourceForm,DBSourceForm,FileSourceForm,S3SourceForm,StreamSourceForm,index}.tsx
            touch "${MODULE_DIR}"/components/preview/{ApiPreview,DatabasePreview,FilePreview,S3Preview,StreamPreview}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/{useApiSource,useDBSource,useFileSource,useS3Source,useStreamSource,index}.ts
            ;;
        "pipeline")
            touch "${MODULE_DIR}"/pages/PipelinesPage.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            touch "${MODULE_DIR}"/components/{PipelineDetails,PipelineForm,PipelineList,PipelineLogs,PipelineMetricsChart,PipelineRuns}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/usePipeline.ts
            touch "${MODULE_DIR}"/hooks/index.ts
            ;;
        "monitoring")
            touch "${MODULE_DIR}"/pages/MonitoringPage.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            touch "${MODULE_DIR}"/components/{AlertsList,HealthStatus,MetricsCard}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/useMonitoring.ts
            touch "${MODULE_DIR}"/hooks/index.ts
            ;;
        "recommendations")
            touch "${MODULE_DIR}"/pages/RecommendationsPage.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            touch "${MODULE_DIR}"/components/{RecommendationCard,RecommendationFilter,RecommendationHistory}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/useRecommendations.ts
            touch "${MODULE_DIR}"/hooks/index.ts
            ;;
        "reports")
            touch "${MODULE_DIR}"/pages/ReportsPage.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            touch "${MODULE_DIR}"/components/{ReportForm,ReportList,ReportViewer}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/useReports.ts
            touch "${MODULE_DIR}"/hooks/index.ts
            ;;
        "decisions")
            touch "${MODULE_DIR}"/pages/DecisionsPage.tsx
            touch "${MODULE_DIR}"/pages/index.ts
            touch "${MODULE_DIR}"/components/{DecisionCard,DecisionDetails,DecisionFilters,DecisionStats,DecisionTimeline}.tsx
            touch "${MODULE_DIR}"/components/index.ts
            touch "${MODULE_DIR}"/hooks/useDecisions.ts
            touch "${MODULE_DIR}"/hooks/index.ts
            ;;
    esac

    echo "${MODULE_NAME} module structure created successfully!"
}

# Create each module
MODULES=("analysis" "auth" "dataSource" "pipeline" "monitoring" "recommendations" "reports" "decisions")

for module in "${MODULES[@]}"; do
    create_module $module
done

echo "All modules created successfully!"