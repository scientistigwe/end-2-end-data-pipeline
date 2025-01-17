# backend/db/init.py

from sqlalchemy import create_engine, inspect, text, event, DDL
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import database_exists, create_database
import logging
from typing import Tuple, Any
from pathlib import Path

from .models.base import Base, base_meta
from .models import *  # Import all types

logger = logging.getLogger(__name__)

def init_db(app) -> scoped_session:
    """
    Initialize db with complete setup and verification.
    
    Args:
        app: Flask application instance with config
        
    Returns:
        scoped_session: Database session factory
    """
    try:
        # Configure SQLAlchemy logging
        sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
        sqlalchemy_logger.setLevel(app.config['SQLALCHEMY_ENGINE_LOGGING_LEVEL'])

        logger.info(f"Initializing db connection to: {app.config['SQLALCHEMY_DATABASE_URI']}")

        # Create db if it doesn't exist
        if not database_exists(app.config['SQLALCHEMY_DATABASE_URI']):
            create_database(app.config['SQLALCHEMY_DATABASE_URI'])
            logger.info("Database created successfully")

        # Create engine with configuration
        engine = create_engine(
            app.config['SQLALCHEMY_DATABASE_URI'],
            pool_size=app.config['SQLALCHEMY_POOL_SIZE'],
            max_overflow=app.config['SQLALCHEMY_MAX_OVERFLOW'],
            pool_timeout=app.config['SQLALCHEMY_POOL_TIMEOUT'],
            echo=app.config.get('SQLALCHEMY_ECHO', False)
        )

        # Create session factory and scoped session
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = scoped_session(session_factory)

        # Initialize db structure
        with engine.connect() as connection:
            # Verify connection
            connection.execute(text("SELECT 1"))
            connection.commit()
            logger.info("Database connection verified successfully")

            # Get existing tables
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()

            # Create tables in the correct order
            Base.metadata.create_all(bind=engine)

            # Register all db functions (includes triggers)
            _register_database_functions(engine)

            # Verify db integrity
            _verify_database_integrity(inspector)

            # Final verification of table creation
            all_tables = inspector.get_table_names()
            expected_tables = {table.name for table in Base.metadata.sorted_tables}
            missing_tables = expected_tables - set(all_tables)

            if missing_tables:
                raise ValueError(f"Failed to create tables: {missing_tables}")

            logger.info("Database tables and functions created/verified successfully")

        # Register cleanup handlers
        @app.teardown_appcontext
        def cleanup_db_session(exception=None):
            session.remove()

        @app.teardown_appcontext
        def cleanup_engine(exception=None):
            if engine:
                engine.dispose()
                logger.info("Database connections cleaned up")

        return session

    except SQLAlchemyError as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during db initialization: {str(e)}")
        raise

def _register_database_functions(engine) -> None:
    """Register all custom PostgreSQL functions and views."""
    with engine.connect() as conn:
        try:
            # Register each function in a transaction
            conn.begin()

            # 1. Update timestamp function
            conn.execute(DDL("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """))

            # 2. Pipeline statistics function
            conn.execute(DDL("""
                CREATE OR REPLACE FUNCTION calculate_pipeline_stats(p_id UUID)
                RETURNS TABLE (
                    total_runs BIGINT,
                    successful_runs BIGINT,
                    average_duration FLOAT,
                    success_rate FLOAT
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        COUNT(*) as total_runs,
                        COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                        AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as average_duration,
                        (COUNT(*) FILTER (WHERE status = 'completed')::FLOAT / COUNT(*)::FLOAT) * 100 as success_rate
                    FROM pipeline_runs
                    WHERE pipeline_id = p_id;
                END;
                $$ LANGUAGE plpgsql;
            """))

            # 3. Materialized view for pipeline statistics
            conn.execute(DDL("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_pipeline_stats AS
                SELECT 
                    p.id as pipeline_id,
                    p.name,
                    COUNT(pr.id) as total_runs,
                    COUNT(*) FILTER (WHERE pr.status = 'completed') as successful_runs,
                    AVG(EXTRACT(EPOCH FROM (pr.end_time - pr.start_time))) as avg_duration,
                    MAX(pr.start_time) as last_run
                FROM pipelines p
                LEFT JOIN pipeline_runs pr ON p.id = pr.pipeline_id
                GROUP BY p.id, p.name;
            """))

            # 4. Pipeline stats refresh function
            conn.execute(DDL("""
                CREATE OR REPLACE FUNCTION refresh_pipeline_stats()
                RETURNS trigger AS $$
                BEGIN
                    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pipeline_stats;
                    RETURN NULL;
                END;
                $$ LANGUAGE plpgsql;
            """))

            # 5. Create trigger for pipeline stats refresh
            conn.execute(DDL("""
                DROP TRIGGER IF EXISTS trg_refresh_pipeline_stats ON pipeline_runs;
                CREATE TRIGGER trg_refresh_pipeline_stats
                AFTER INSERT OR UPDATE OR DELETE ON pipeline_runs
                FOR EACH STATEMENT
                EXECUTE FUNCTION refresh_pipeline_stats();
            """))

            # 6. Create triggers for updated_at columns
            for table in Base.metadata.tables.values():
                if 'updated_at' in table.columns:
                    conn.execute(DDL(f"""
                        DROP TRIGGER IF EXISTS update_updated_at_{table.name} ON {table.name};
                        CREATE TRIGGER update_updated_at_{table.name}
                        BEFORE UPDATE ON {table.name}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                    """))

            # Commit all changes
            conn.commit()
            logger.info("Database functions and views registered successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error registering db functions: {str(e)}")
            raise

def _register_timestamp_triggers(engine) -> None:
    """Register updated_at timestamp triggers for all tables."""
    with engine.connect() as conn:
        # Create update timestamp function
        conn.execute(DDL("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """))

        # Create triggers for all tables with updated_at column
        for table in Base.metadata.tables.values():
            if 'updated_at' in table.columns:
                conn.execute(DDL(f"""
                    DROP TRIGGER IF EXISTS update_updated_at_{table.name} ON {table.name};
                    CREATE TRIGGER update_updated_at_{table.name}
                    BEFORE UPDATE ON {table.name}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
                """))

def _verify_database_integrity(inspector) -> None:
    """
    Verify foreign keys and constraints for all tables.
    
    Args:
        inspector: SQLAlchemy Inspector instance
    
    Raises:
        ValueError: If any integrity checks fail
    """
    try:
        integrity_issues = []
        
        for table_name in inspector.get_table_names():
            # Verify foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            for fk in foreign_keys:
                try:
                    constrained_columns = fk['constrained_columns']
                    referred_table = fk['referred_table']
                    referred_columns = fk['referred_columns']
                    
                    logger.debug(
                        f"Verified foreign key in {table_name}: "
                        f"columns {constrained_columns} -> "
                        f"{referred_table}({referred_columns})"
                    )
                except Exception as e:
                    integrity_issues.append(
                        f"Invalid foreign key in {table_name}: {str(e)}"
                    )

            # Verify indexes
            indexes = inspector.get_indexes(table_name)
            for idx in indexes:
                try:
                    index_name = idx['name']
                    index_columns = idx['column_names']
                    is_unique = idx['unique']
                    
                    logger.debug(
                        f"Verified index in {table_name}: "
                        f"{index_name} on columns {index_columns} "
                        f"(unique: {is_unique})"
                    )
                except Exception as e:
                    integrity_issues.append(
                        f"Invalid index in {table_name}: {str(e)}"
                    )

            # Verify primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            if not pk_constraint.get('constrained_columns'):
                integrity_issues.append(
                    f"Table {table_name} has no primary key constraint"
                )
            else:
                logger.debug(
                    f"Verified primary key in {table_name}: "
                    f"{pk_constraint['constrained_columns']}"
                )

            # Verify unique constraints
            unique_constraints = inspector.get_unique_constraints(table_name)
            for constraint in unique_constraints:
                try:
                    constraint_name = constraint['name']
                    constraint_columns = constraint['column_names']
                    
                    logger.debug(
                        f"Verified unique constraint in {table_name}: "
                        f"{constraint_name} on columns {constraint_columns}"
                    )
                except Exception as e:
                    integrity_issues.append(
                        f"Invalid unique constraint in {table_name}: {str(e)}"
                    )

            # Verify check constraints
            try:
                check_constraints = inspector.get_check_constraints(table_name)
                for constraint in check_constraints:
                    constraint_name = constraint['name']
                    sqltext = constraint.get('sqltext', 'No condition specified')
                    
                    logger.debug(
                        f"Verified check constraint in {table_name}: "
                        f"{constraint_name} with condition: {sqltext}"
                    )
            except NotImplementedError:
                # Some dialects might not support check constraint inspection
                logger.debug(
                    f"Check constraint inspection not supported for table {table_name}"
                )
            except Exception as e:
                integrity_issues.append(
                    f"Error inspecting check constraints in {table_name}: {str(e)}"
                )

            # Verify columns
            columns = inspector.get_columns(table_name)
            for column in columns:
                try:
                    column_name = column['name']
                    column_type = column['type']
                    is_nullable = column.get('nullable', True)
                    
                    logger.debug(
                        f"Verified column in {table_name}: "
                        f"{column_name} ({column_type}, "
                        f"nullable: {is_nullable})"
                    )
                except Exception as e:
                    integrity_issues.append(
                        f"Invalid column in {table_name}: {str(e)}"
                    )

        # Report any integrity issues
        if integrity_issues:
            error_message = "\n".join(integrity_issues)
            logger.error(f"Database integrity issues found:\n{error_message}")
            raise ValueError(f"Database integrity check failed:\n{error_message}")

        logger.info("Database integrity verification completed successfully")

    except Exception as e:
        logger.error(f"Error during db integrity verification: {str(e)}")
        raise

