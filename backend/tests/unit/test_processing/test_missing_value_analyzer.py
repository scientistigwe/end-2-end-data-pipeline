import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from backend.backend.data_pipeline.quality_analysis.data_issue_analyser.basic_data_validation.analyse_missing_value import \
    MissingValueAnalyzer, MissingValuePattern, MissingMechanism


@pytest.fixture
def sample_data():
    """Create sample dataset for testing."""
    np.random.seed(42)
    size = 1000

    df = pd.DataFrame({
        'complete_col': range(size),  # No missing values
        'random_missing': np.random.normal(100, 15, size),  # Random missing
        'structural_missing': np.random.normal(50, 10, size),  # Structural missing
        'categorical': np.random.choice(['A', 'B', 'C'], size),  # Categorical
        'timestamp': pd.date_range('2024-01-01', periods=size, freq='h')
    })

    # Add missing values
    df.loc[np.random.choice(size, 100), 'random_missing'] = np.nan  # 10% random missing
    df.loc[df['categorical'] == 'A', 'structural_missing'] = np.nan  # Structural missing

    return df


@pytest.fixture
def analyzer():
    return MissingValueAnalyzer()


def test_analyzer_initialization(analyzer):
    assert isinstance(analyzer, MissingValueAnalyzer)


def test_complete_column(analyzer, sample_data):
    results = analyzer.analyze(sample_data)
    assert 'complete_col' not in results


def test_random_missing(analyzer, sample_data):
    results = analyzer.analyze(sample_data)
    assert 'random_missing' in results
    result = results['random_missing']
    assert isinstance(result.pattern, MissingValuePattern)
    assert isinstance(result.mechanism, MissingMechanism)
    assert 0 < result.missing_percentage <= 15


def test_structural_missing(analyzer, sample_data):
    results = analyzer.analyze(sample_data)
    assert 'structural_missing' in results
    result = results['structural_missing']
    assert isinstance(result.pattern, MissingValuePattern)
    assert isinstance(result.mechanism, MissingMechanism)


def test_empty_dataframe(analyzer):
    empty_df = pd.DataFrame()
    results = analyzer.analyze(empty_df)
    assert len(results) == 0


def test_all_missing_column(analyzer):
    df = pd.DataFrame({'all_missing': [np.nan] * 100})
    results = analyzer.analyze(df)
    assert 'all_missing' in results
    assert results['all_missing'].missing_percentage == 100
    assert results['all_missing'].pattern == MissingValuePattern.COMPLETE


def test_single_missing_value(analyzer):
    df = pd.DataFrame({'single_missing': [1] * 99 + [np.nan]})
    results = analyzer.analyze(df)
    assert 'single_missing' in results
    assert results['single_missing'].missing_percentage == 1


def test_recommendation_format(analyzer, sample_data):
    results = analyzer.analyze(sample_data)
    for col, result in results.items():
        assert isinstance(result.recommendation, dict)
        assert 'action' in result.recommendation
        assert 'description' in result.recommendation
        assert 'reason' in result.recommendation


def test_large_dataset_performance(analyzer):
    size = 100_000
    df = pd.DataFrame({
        'large_col': np.random.normal(0, 1, size)
    })
    df.loc[np.random.choice(size, size // 10)] = np.nan

    start_time = datetime.now()
    results = analyzer.analyze(df)
    execution_time = (datetime.now() - start_time).total_seconds()

    assert execution_time < 10  # Should complete within 10 seconds
    assert 'large_col' in results
