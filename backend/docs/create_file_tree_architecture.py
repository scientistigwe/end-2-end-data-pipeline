import os


def create_project_structure(base_path):
    directories = [
        # Backend structure
        "analyst_pa/backend/core/authentication",
        "analyst_pa/backend/core/control",
        "analyst_pa/backend/core/messaging",
        "analyst_pa/backend/core/registry",
        "analyst_pa/backend/processing/quality/analyzers",
        "analyst_pa/backend/processing/quality/detectors",
        "analyst_pa/backend/processing/quality/resolvers",
        "analyst_pa/backend/processing/insights/generators",
        "analyst_pa/backend/processing/insights/validation",
        "analyst_pa/backend/processing/decisions/processor",
        "analyst_pa/backend/processing/decisions/validation",
        "analyst_pa/backend/processing/advanced_analytics/processors",
        "analyst_pa/backend/processing/advanced_analytics/types",
        "analyst_pa/backend/infrastructure/docker",
        "analyst_pa/backend/infrastructure/celery",
        "analyst_pa/backend/infrastructure/prometheus",
        "analyst_pa/backend/source_handlers/api",
        "analyst_pa/backend/source_handlers/file",
        "analyst_pa/backend/source_handlers/db",
        "analyst_pa/backend/monitoring/collectors",
        "analyst_pa/backend/monitoring/alerts",
        "analyst_pa/backend/monitoring/dashboards",
        "analyst_pa/backend/subscription/managers",
        "analyst_pa/backend/subscription/payment",
        "analyst_pa/backend/utils",

        # Frontend structure
        "analyst_pa/frontend/src/components/analysis",
        "analyst_pa/frontend/src/components/common",
        "analyst_pa/frontend/src/components/dashboard",
        "analyst_pa/frontend/src/pages",
        "analyst_pa/frontend/src/services",
        "analyst_pa/frontend/src/utils",
        "analyst_pa/frontend/public/assets",

        # Tests structure
        "analyst_pa/tests/unit/core",
        "analyst_pa/tests/unit/processing",
        "analyst_pa/tests/unit/services",
        "analyst_pa/tests/integration/workflows",
        "analyst_pa/tests/integration/services",
        "analyst_pa/tests/e2e/features"
    ]

    files = [
        # Backend files
        "analyst_pa/backend/core/authentication/jwt_handler.py",
        "analyst_pa/backend/core/authentication/security.py",
        "analyst_pa/backend/core/authentication/permissions.py",
        "analyst_pa/backend/core/control/cpm.py",
        "analyst_pa/backend/core/control/state_manager.py",
        "analyst_pa/backend/core/messaging/broker.py",
        "analyst_pa/backend/core/messaging/event_types.py",
        "analyst_pa/backend/core/messaging/publishers.py",
        "analyst_pa/backend/core/registry/component_registry.py",
        "analyst_pa/backend/core/registry/route_registry.py",
        "analyst_pa/backend/processing/quality/analyzers/date_analyzer.py",
        "analyst_pa/backend/processing/quality/analyzers/numeric_analyzer.py",
        "analyst_pa/backend/processing/quality/analyzers/text_analyzer.py",
        "analyst_pa/backend/processing/quality/detectors/anomaly_detector.py",
        "analyst_pa/backend/processing/quality/detectors/pattern_detector.py",
        "analyst_pa/backend/processing/quality/resolvers/auto_resolver.py",
        "analyst_pa/backend/processing/quality/resolvers/manual_resolver.py",
        "analyst_pa/backend/processing/insights/generators/pattern_insights.py",
        "analyst_pa/backend/processing/insights/generators/trend_insights.py",
        "analyst_pa/backend/processing/insights/validation/business_goal_insights.py",
        "analyst_pa/backend/processing/insights/validation/pattern_validator.py",
        "analyst_pa/backend/processing/decisions/processor/decision_processor.py",
        "analyst_pa/backend/processing/decisions/processor/recommendation_engine.py",
        "analyst_pa/backend/processing/decisions/validation/decision_tracker.py",
        "analyst_pa/backend/processing/decisions/validation/decision_validator.py",
        "analyst_pa/backend/processing/advanced_analytics/processors/analytics_processor.py",
        "analyst_pa/backend/processing/advanced_analytics/types/analysis_types.py",
        "analyst_pa/backend/infrastructure/docker/Dockerfile",
        "analyst_pa/backend/infrastructure/docker/docker-compose.yml",
        "analyst_pa/backend/infrastructure/celery/tasks.py",
        "analyst_pa/backend/infrastructure/celery/config.py",
        "analyst_pa/backend/infrastructure/prometheus/config.yml",
        "analyst_pa/backend/infrastructure/prometheus/alerts.yml",
        "analyst_pa/backend/source_handlers/api/api_handler.py",
        "analyst_pa/backend/source_handlers/api/api_validator.py",
        "analyst_pa/backend/source_handlers/file/file_handler.py",
        "analyst_pa/backend/source_handlers/file/file_validator.py",
        "analyst_pa/backend/source_handlers/db/db_handler.py",
        "analyst_pa/backend/source_handlers/db/db_validator.py",
        "analyst_pa/backend/monitoring/collectors/metric_collector.py",
        "analyst_pa/backend/monitoring/collectors/log_collector.py",
        "analyst_pa/backend/monitoring/alerts/alert_manager.py",
        "analyst_pa/backend/monitoring/dashboards/grafana_config.json",
        "analyst_pa/backend/subscription/managers/subscription_manager.py",
        "analyst_pa/backend/subscription/managers/usage_tracker.py",
        "analyst_pa/backend/subscription/payment/payment_processor.py",
        "analyst_pa/backend/subscription/payment/payment_validator.py",
        "analyst_pa/backend/utils/encryption.py",
        "analyst_pa/backend/utils/validation.py",
        "analyst_pa/backend/utils/formatters.py",

        # Frontend files
        "analyst_pa/frontend/src/components/analysis/QualityReview.tsx",
        "analyst_pa/frontend/src/components/analysis/InsightDisplay.tsx",
        "analyst_pa/frontend/src/components/common/Navigation.tsx",
        "analyst_pa/frontend/src/components/common/Controls.tsx",
        "analyst_pa/frontend/src/components/dashboard/MetricsDisplay.tsx",
        "analyst_pa/frontend/src/components/dashboard/StatusPanel.tsx",
        "analyst_pa/frontend/src/pages/Analysis.tsx",
        "analyst_pa/frontend/src/pages/Dashboard.tsx",
        "analyst_pa/frontend/src/pages/Settings.tsx",
        "analyst_pa/frontend/src/services/api.ts",
        "analyst_pa/frontend/src/services/auth.ts",
        "analyst_pa/frontend/src/utils/formatters.ts",
        "analyst_pa/frontend/src/utils/validation.ts",
        "analyst_pa/frontend/public/index.html",

        # Tests files (empty __init__.py files for Python modules)
        "analyst_pa/tests/unit/__init__.py",
        "analyst_pa/tests/integration/__init__.py",
        "analyst_pa/tests/e2e/__init__.py"
    ]

    # Create directories
    for directory in directories:
        os.makedirs(os.path.join(base_path, directory), exist_ok=True)

    # Create files
    for file in files:
        full_path = os.path.join(base_path, file)
        with open(full_path, "w") as f:
            pass  # Create empty file


# Specify the base directory
base_path = os.getcwd()  # Change this to your desired base path
create_project_structure(base_path)
print(f"Project structure created at {base_path}")
