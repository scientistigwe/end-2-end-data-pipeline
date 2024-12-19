-- migrations/functions.sql
-- Automatic timestamp management
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Pipeline statistics
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

-- Materialized view for pipeline statistics
CREATE MATERIALIZED VIEW mv_pipeline_stats AS
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

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_pipeline_stats()
RETURNS trigger AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pipeline_stats;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;