analyst_pa/
├── backend/
│   ├── core/
│   │   ├── authentication/
│   │   │   ├── jwt_handler.py
│   │   │   ├── security.py
│   │   │   └── permissions.py
│   │   │
│   │   ├── control/
│   │   │   ├── cpm.py
│   │   │   └── state_manager.py
│   │   │
│   │   ├── messaging/
│   │   │   ├── broker.py
│   │   │   ├── event_types.py
│   │   │   └── publishers.py
│   │   │
│   │   ├── staging/
│   │   │   ├── staging_manager.py
│   │   │   ├── storage_manager.py
│   │   │   └── cleanup_manager.py
│   │   │
│   │   ├── handlers/
│   │   │   ├── base/
│   │   │   │   ├── base_handler.py
│   │   │   │   └── handler_types.py
│   │   │   │
│   │   │   ├── channel/
│   │   │   │   ├── quality_handler.py
│   │   │   │   ├── insight_handler.py
│   │   │   │   ├── analytics_handler.py
│   │   │   │   ├── monitoring_handler.py
│   │   │   │   ├── decision_handler.py
│   │   │   │   ├── recommendation_handler.py
│   │   │   │   └── report_handler.py
│   │   │   │
│   │   │   └── process/
│   │   │       ├── core_process_handler.py
│   │   │       └── error_handler.py
│   │   │
│   │   ├── managers/
│   │   │   ├── base/
│   │   │   │   ├── base_manager.py
│   │   │   │   └── manager_types.py
│   │   │   │
│   │   │   ├── quality_manager.py
│   │   │   ├── insight_manager.py
│   │   │   ├── analytics_manager.py
│   │   │   ├── monitoring_manager.py
│   │   │   ├── decision_manager.py
│   │   │   ├── recommendation_manager.py
│   │   │   └── report_manager.py
│   │   │
│   │   └── registry/
│   │       ├── component_registry.py
│   │       └── route_registry.py
│   │
│   ├── data_processing/
│   │   ├── quality/
│   │   │   ├── processor/
│   │   │   │   └── quality_processor.py
│   │   │   ├── analyzers/
│   │   │   │   ├── date_analyzer.py
│   │   │   │   ├── numeric_analyzer.py
│   │   │   │   └── text_analyzer.py
│   │   │   ├── detectors/
│   │   │   │   ├── anomaly_detector.py
│   │   │   │   └── pattern_detector.py
│   │   │   └── resolvers/
│   │   │       ├── auto_resolver.py
│   │   │       └── manual_resolver.py
│   │   │
│   │   ├── insights/
│   │   │   ├── processor/
│   │   │   │   └── insight_processor.py
│   │   │   ├── generators/
│   │   │   │   ├── pattern_insights.py
│   │   │   │   └── trend_insights.py
│   │   │   └── validators/
│   │   │       ├── business_validator.py
│   │   │       └── data_validator.py
│   │   │
│   │   ├── advanced_analytics/
│   │   │   ├── processor/
│   │   │   │   └── analytics_processor.py
│   │   │   ├── modules/
│   │   │   │   ├── data_preparation/
│   │   │   │   ├── feature_engineering/
│   │   │   │   ├── model_training/
│   │   │   │   ├── model_evaluation/
│   │   │   │   └── visualization/
│   │   │   └── models/
│   │   │       └── analysis_models.py
│   │   │
│   │   ├── monitoring/
│   │   │   ├── processor/
│   │   │   │   └── monitoring_processor.py
│   │   │   ├── collectors/
│   │   │   │   ├── metric_collector.py
│   │   │   │   └── log_collector.py
│   │   │   └── analyzers/
│   │   │       ├── performance_analyzer.py
│   │   │       └── resource_analyzer.py
│   │   │
│   │   ├── decisions/
│   │   │   ├── processor/
│   │   │   │   └── decision_processor.py
│   │   │   ├── engines/
│   │   │   │   ├── decision_engine.py
│   │   │   │   └── optimization_engine.py
│   │   │   └── validators/
│   │   │       ├── impact_analyzer.py
│   │   │       └── constraint_validator.py
│   │   │
│   │   ├── recommendations/
│   │   │   ├── processor/
│   │   │   │   └── recommendation_processor.py
│   │   │   ├── generators/
│   │   │   │   ├── recommendation_generator.py
│   │   │   │   └── prioritization_engine.py
│   │   │   └── validators/
│   │   │       ├── relevance_validator.py
│   │   │       └── impact_validator.py
│   │   │
│   │   └── reports/
│   │       ├── processor/
│   │       │   └── report_processor.py
│   │       ├── generators/
│   │       │   ├── report_generator.py
│   │       │   └── template_engine.py
│   │       └── formatters/
│   │           ├── pdf_formatter.py
│   │           └── html_formatter.py
│   │
│   ├── infrastructure/
│   │   ├── docker/
│   │   │   ├── Dockerfile
│   │   │   └── docker-compose.yml
│   │   ├── celery/
│   │   │   ├── tasks.py
│   │   │   └── config.py
│   │   └── prometheus/
│   │       ├── config.yml
│   │       └── alerts.yml
│   │
│   ├── source_handlers/
│   │   ├── api/
│   │   │   ├── api_handler.py
│   │   │   └── api_validator.py
│   │   ├── file/
│   │   │   ├── file_handler.py
│   │   │   └── file_validator.py
│   │   └── database/
│   │       ├── db_handler.py
│   │       └── db_validator.py
│   │
│   └── utils/
│       ├── encryption.py
│       ├── validators.py
│       └── formatters.py
│
├── frontend/
│   └── [Frontend structure remains the same]
│
└── tests/
    ├── unit/
    │   ├── core/
    │   │   ├── managers/
    │   │   ├── handlers/
    │   │   └── processors/
    │   └── processing/
    │       ├── quality/
    │       ├── insights/
    │       ├── analytics/
    │       ├── monitoring/
    │       ├── decisions/
    │       └── recommendations/
    │
    ├── integration/
    │   └── workflows/
    │       ├── quality_flow/
    │       ├── insight_flow/
    │       ├── analytics_flow/
    │       ├── monitoring_flow/
    │       ├── decision_flow/
    │       └── recommendation_flow/
    │
    └── e2e/
        └── features/