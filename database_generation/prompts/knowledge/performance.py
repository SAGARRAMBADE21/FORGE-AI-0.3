"""Performance optimization knowledge base."""
PERFORMANCE_XML = """
<performance>
    <query_optimization>
        <rule name="select_only_needed">
            <description>Never use SELECT *</description>
            <wrong>SELECT * FROM users WHERE id = $1</wrong>
            <correct>SELECT id, email, name FROM users WHERE id = $1</correct>
            <reason>Reduces I/O, network transfer, and memory usage</reason>
        </rule>

        <rule name="filter_early">
            <description>Apply WHERE before JOINs when possible</description>
            <wrong>
SELECT * FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.status = 'pending'
            </wrong>
            <correct>
SELECT * FROM (
    SELECT * FROM orders WHERE status = 'pending'
) o
JOIN order_items oi ON o.id = oi.order_id
            </correct>
        </rule>

        <rule name="avoid_functions_on_indexed_columns">
            <description>Functions prevent index usage</description>
            <wrong>
SELECT * FROM users WHERE LOWER(email) = 'a@b.com';
SELECT * FROM orders WHERE YEAR(created_at) = 2024;
            </wrong>
            <correct>
SELECT * FROM users WHERE email = 'a@b.com'; -- store lowercase
SELECT * FROM orders WHERE created_at >= '2024-01-01' AND created_at &lt; '2025-01-01';
            </correct>
        </rule>

        <rule name="use_exists_over_in">
            <description>EXISTS often faster than IN for subqueries</description>
            <wrong>SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)</wrong>
            <correct>SELECT * FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id)</correct>
        </rule>

        <rule name="avoid_not_in_with_nulls">
            <description>NOT IN fails with NULL values</description>
            <wrong>SELECT * FROM users WHERE id NOT IN (SELECT user_id FROM banned)</wrong>
            <correct>SELECT * FROM users u WHERE NOT EXISTS (SELECT 1 FROM banned b WHERE b.user_id = u.id)</correct>
            <reason>If subquery contains NULL, NOT IN returns empty result</reason>
        </rule>

        <rule name="limit_results">
            <description>Always paginate large result sets</description>
            <wrong>SELECT * FROM posts ORDER BY created_at DESC OFFSET 10000 LIMIT 20</wrong>
            <correct>SELECT * FROM posts WHERE created_at &lt; $cursor ORDER BY created_at DESC LIMIT 20</correct>
            <reason>OFFSET scans all skipped rows; keyset pagination is O(1)</reason>
        </rule>
    </query_optimization>

    <join_optimization>
        <rule name="index_join_columns">
            <description>Always index columns used in JOINs</description>
            <sql>
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
            </sql>
        </rule>

        <rule name="join_order">
            <description>Start with most filtered/smallest table</description>
        </rule>

        <rule name="use_appropriate_join">
            <description>Choose correct join type</description>
            <join type="INNER">Only matching rows</join>
            <join type="LEFT">All from left, matching from right</join>
            <join type="RIGHT">All from right, matching from left (rarely needed)</join>
            <join type="CROSS">Cartesian product (avoid unless intended)</join>
        </rule>
    </join_optimization>

    <write_optimization>
        <rule name="batch_inserts">
            <wrong>
INSERT INTO logs (msg) VALUES ('a');
INSERT INTO logs (msg) VALUES ('b');
INSERT INTO logs (msg) VALUES ('c');
            </wrong>
            <correct>INSERT INTO logs (msg) VALUES ('a'), ('b'), ('c');</correct>
            <batch_sizes>
                <size database="postgresql">1000-10000 rows per batch</size>
                <size database="mysql">1000-5000 rows per batch</size>
                <size database="sqlserver">1000 rows per batch</size>
            </batch_sizes>
        </rule>

        <rule name="bulk_operations">
            <description>Single statement better than loop</description>
            <correct>UPDATE products SET price = price * 1.1 WHERE category_id = $1</correct>
        </rule>

        <rule name="disable_constraints_for_bulk">
            <postgresql>
BEGIN;
ALTER TABLE t DISABLE TRIGGER ALL;
-- bulk operations
ALTER TABLE t ENABLE TRIGGER ALL;
COMMIT;
            </postgresql>
            <mysql>
SET FOREIGN_KEY_CHECKS = 0;
-- bulk operations
SET FOREIGN_KEY_CHECKS = 1;
            </mysql>
            <sqlserver>
ALTER TABLE t NOCHECK CONSTRAINT ALL;
-- bulk operations
ALTER TABLE t CHECK CONSTRAINT ALL;
            </sqlserver>
        </rule>
    </write_optimization>

    <connection_management>
        <pooling>
            <min_connections>5</min_connections>
            <max_connections>20-50</max_connections>
            <idle_timeout>300 seconds</idle_timeout>
            <max_lifetime>1800 seconds</max_lifetime>
        </pooling>
        <rules>
            <rule>Never open/close per query</rule>
            <rule>Use connection pool</rule>
            <rule>Release connections quickly</rule>
            <rule>Monitor active connections</rule>
        </rules>
    </connection_management>

    <caching>
        <application_cache>
            <tool>Redis or Memcached</tool>
            <cache_what>
                <item>Hot data (frequently accessed)</item>
                <item>Session data</item>
                <item>Computed results</item>
                <item>API responses</item>
            </cache_what>
            <invalidation>
                <strategy name="ttl">Time-based expiration</strategy>
                <strategy name="event">Invalidate on write</strategy>
                <strategy name="write_through">Update cache on write</strategy>
            </invalidation>
        </application_cache>

        <query_cache>
            <postgresql>
-- Materialized views
CREATE MATERIALIZED VIEW monthly_sales AS
SELECT date_trunc('month', created_at) AS month, SUM(total) AS revenue
FROM orders GROUP BY 1;

REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_sales;
            </postgresql>
            <mysql>Query cache removed in 8.0, use application caching</mysql>
        </query_cache>
    </caching>

    <partitioning>
        <when_to_use>
            <criterion>Tables over 10 million rows</criterion>
            <criterion>Time-series data (logs, events)</criterion>
            <criterion>Data that can be archived</criterion>
            <criterion>Multi-tenant with tenant isolation</criterion>
        </when_to_use>

        <types>
            <type name="range">
                <use_case>Date ranges, numeric ranges</use_case>
                <postgresql>
CREATE TABLE orders (
    id UUID, created_at TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE orders_2024_q1 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
                </postgresql>
                <mysql>
CREATE TABLE orders (
    id INT, created_at DATETIME NOT NULL
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025)
);
                </mysql>
            </type>

            <type name="list">
                <use_case>Categorical values (region, status)</use_case>
                <postgresql>
CREATE TABLE users (id UUID, region VARCHAR(10))
PARTITION BY LIST (region);

CREATE TABLE users_us PARTITION OF users FOR VALUES IN ('us-east', 'us-west');
CREATE TABLE users_eu PARTITION OF users FOR VALUES IN ('eu-west', 'eu-central');
                </postgresql>
            </type>

            <type name="hash">
                <use_case>Distribute evenly across partitions</use_case>
                <postgresql>
CREATE TABLE sessions (id UUID, user_id UUID)
PARTITION BY HASH (user_id);

CREATE TABLE sessions_0 PARTITION OF sessions FOR VALUES WITH (MODULUS 4, REMAINDER 0);
                </postgresql>
            </type>
        </types>
    </partitioning>

    <monitoring>
        <key_metrics>
            <metric>Query execution time</metric>
            <metric>Cache hit ratio (target: >90%)</metric>
            <metric>Index hit ratio (target: >95%)</metric>
            <metric>Connection count</metric>
            <metric>Lock waits</metric>
            <metric>Replication lag</metric>
            <metric>Disk I/O</metric>
            <metric>Memory usage</metric>
        </key_metrics>

        <postgresql_queries>
            <slow_queries>SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 20</slow_queries>
            <table_bloat>SELECT relname, n_dead_tup, n_live_tup FROM pg_stat_user_tables</table_bloat>
            <index_usage>SELECT indexrelname, idx_scan FROM pg_stat_user_indexes</index_usage>
        </postgresql_queries>

        <mysql_queries>
            <slow_query_log>SET GLOBAL slow_query_log = 'ON'</slow_query_log>
            <status>SHOW GLOBAL STATUS LIKE 'Slow_queries'</status>
        </mysql_queries>
    </monitoring>

    <explain_analysis>
        <postgresql>
            <command>EXPLAIN ANALYZE SELECT ...</command>
            <good_signs>Index Scan, Index Only Scan, Bitmap Index Scan</good_signs>
            <bad_signs>Seq Scan on large tables, Nested Loop on large sets</bad_signs>
        </postgresql>
        <mysql>
            <command>EXPLAIN SELECT ...</command>
            <good_type>const, eq_ref, ref, range</good_type>
            <bad_type>ALL (full table scan)</bad_type>
        </mysql>
    </explain_analysis>
</performance>
"""
