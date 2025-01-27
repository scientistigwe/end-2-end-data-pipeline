import os
from pathlib import Path


def create_data_pipeline_structure():
    # Base directory
    base_dir = Path('backend')

    # Modules to create
    modules = [
        'data_preparation',
        'feature_engineering',
        'model_training',
        'model_evaluation',
        'visualization'
    ]

    # Files for each module
    module_files = {
        'data_preparation': [
            'data_cleaner.py',
            'data_transformer.py',
            'data_validator.py'
        ],
        'feature_engineering': [
            'feature_extractor.py',
            'feature_selector.py',
            'feature_transformer.py'
        ],
        'model_training': [
            'model_selector.py',
            'model_trainer.py',
            'model_tuner.py'
        ],
        'model_evaluation': [
            'performance_evaluator.py',
            'bias_checker.py',
            'stability_tester.py'
        ],
        'visualization': [
            'chart_generator.py',
            'graph_generator.py',
            'dashboard_builder.py'
        ]
    }

    # Create base directory
    base_dir.mkdir(parents=True, exist_ok=True)

    # Create modules directory
    modules_dir = base_dir / 'modules'
    modules_dir.mkdir(exist_ok=True)

    # Create module directories and files
    for module in modules:
        # Create module directory
        module_path = modules_dir / module
        module_path.mkdir(exist_ok=True)

        # Create __init__.py
        init_file = module_path / '__init__.py'
        init_file.touch()

        # Write initialization content to __init__.py
        init_file.write_text(f"# Package initialization for {module} module")

        # Create module-specific files
        for file in module_files[module]:
            (module_path / file).touch()

create_data_pipeline_structure()