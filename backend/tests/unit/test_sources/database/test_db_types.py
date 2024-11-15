# test_db_types.py

import pytest
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_types import DatabaseType


def test_database_type():
    assert DatabaseType.POSTGRESQL == DatabaseType.from_string('postgresql')

    with pytest.raises(ValueError):
        DatabaseType.from_string('invalid_type')

### Integration Test

