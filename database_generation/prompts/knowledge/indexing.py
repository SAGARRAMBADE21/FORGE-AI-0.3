"""Indexing strategies knowledge base."""
INDEXING_XML = """
<indexing>
    <index_types>
        <type name="btree" default="yes">
            <description>Balanced tree, default for most databases</description>
            <best_for>Equality, range queries, sorting</best_for>
            <operators>=, &lt;, &gt;, &lt;=, &gt;=, BETWEEN, IN, LIKE 'prefix%'</operators>
            <postgresql>CREATE INDEX idx ON t(col)</postgresql>
            <mysql>CREATE INDEX idx ON t(col)</mysql>
            <mariadb>CREATE INDEX idx ON t(col)</mariadb>
            <sqlite>CREATE INDEX idx ON t(col)</sqlite>
            <sqlserver>CREATE INDEX idx ON t(col)</sqlserver>
            <oracle>CREATE INDEX idx ON t(col)</oracle>
        </type>
        <type name="hash">
            <description>Hash-based lookup</description>
            <best_for>Equality only, very fast</best_for>
            <operators>=</operators>
            <postgresql>CREATE INDEX idx ON t USING HASH(col)</postgresql>
            <mysql>MEMORY engine only</mysql>
            <mariadb>MEMORY engine only</mariadb>
            <oracle>CREATE INDEX idx ON t(col) ORGANIZATION HASH</oracle>
        </type>
        <type name="gin">
            <description>Generalized Inverted Index</description>
            <best_for>Arrays, JSONB, full-text search</best_for>
            <postgresql>CREATE INDEX idx ON t USING GIN(col)</postgresql>
        </type>
        <type name="gist">
            <description>Generalized Search Tree</description>
            <best_for>Geometric data, range types, full-text</best_for>
            <postgresql>CREATE INDEX idx ON t USING GIST(col)</postgresql>
        </type>
        <type name="brin">
            <description>Block Range Index</description>
            <best_for>Large tables with natural ordering</best_for>
            <postgresql>CREATE INDEX idx ON t USING BRIN(col)</postgresql>
        </type>
        <type name="fulltext">
            <description>Full-text search index</description>
            <postgresql>GIN on TSVECTOR column</postgresql>
            <mysql>CREATE FULLTEXT INDEX idx ON t(col)</mysql>
            <mariadb>CREATE FULLTEXT INDEX idx ON t(col)</mariadb>
            <sqlserver>CREATE FULLTEXT INDEX ON t(col)</sqlserver>
            <oracle>CREATE INDEX idx ON t(col) INDEXTYPE IS CTXSYS.CONTEXT</oracle>
            <mongodb>db.t.createIndex({col: "text"})</mongodb>
        </type>
        <type name="spatial">
            <description>Geographic/geometric index</description>
            <postgresql>CREATE INDEX idx ON t USING GIST(col)</postgresql>
            <mysql>CREATE SPATIAL INDEX idx ON t(col)</mysql>
            <mariadb>CREATE SPATIAL INDEX idx ON t(col)</mariadb>
            <sqlserver>CREATE SPATIAL INDEX idx ON t(col)</sqlserver>
            <oracle>CREATE INDEX idx ON t(col) INDEXTYPE IS MDSYS.SPATIAL_INDEX</oracle>
            <mongodb>db.t.createIndex({col: "2dsphere"})</mongodb>
        </type>
    </index_types>

    <when_to_index>
        <always_index>
            <item>Primary keys (automatic)</item>
            <item>Foreign keys (CRITICAL - not automatic!)</item>
            <item>Columns in WHERE clauses</item>
            <item>Columns in JOIN conditions</item>
            <item>Columns in ORDER BY</item>
        </always_index>
        <consider_indexing>
            <item>Columns in GROUP BY</item>
            <item>High cardinality columns</item>
            <item>UNIQUE constraints</item>
            <item>Frequently filtered columns</item>
        </consider_indexing>
        <avoid_indexing>
            <item>Small tables (&lt;1000 rows)</item>
            <item>Low cardinality (boolean, status with few values)</item>
            <item>Frequently updated columns</item>
            <item>Wide columns (long text)</item>
        </avoid_indexing>
    </when_to_index>

    <index_patterns>
        <pattern name="single_column">
            <use_case>Equality or range on one column</use_case>
            <postgresql>CREATE INDEX idx_users_email ON users(email)</postgresql>
            <mysql>CREATE INDEX idx_users_email ON users(email)</mysql>
            <mariadb>CREATE INDEX idx_users_email ON users(email)</mariadb>
            <sqlite>CREATE INDEX idx_users_email ON users(email)</sqlite>
            <sqlserver>CREATE INDEX idx_users_email ON users(email)</sqlserver>
            <oracle>CREATE INDEX idx_users_email ON users(email)</oracle>
            <mongodb>db.users.createIndex({email: 1})</mongodb>
        </pattern>

        <pattern name="composite">
            <use_case>Multiple column queries</use_case>
            <critical>Column order matters! Leftmost prefix rule.</critical>
            <postgresql>CREATE INDEX idx ON orders(user_id, status, created_at)</postgresql>
            <mysql>CREATE INDEX idx ON orders(user_id, status, created_at)</mysql>
            <mariadb>CREATE INDEX idx ON orders(user_id, status, created_at)</mariadb>
            <sqlite>CREATE INDEX idx ON orders(user_id, status, created_at)</sqlite>
            <sqlserver>CREATE INDEX idx ON orders(user_id, status, created_at)</sqlserver>
            <oracle>CREATE INDEX idx ON orders(user_id, status, created_at)</oracle>
            <mongodb>db.orders.createIndex({user_id: 1, status: 1, created_at: -1})</mongodb>
            <leftmost_prefix_rule>
                <index>CREATE INDEX idx_abc ON t(a, b, c)</index>
                <uses_index>WHERE a = 1</uses_index>
                <uses_index>WHERE a = 1 AND b = 2</uses_index>
                <uses_index>WHERE a = 1 AND b = 2 AND c = 3</uses_index>
                <partial_use>WHERE a = 1 AND c = 3 (only uses a)</partial_use>
                <no_use>WHERE b = 2</no_use>
                <no_use>WHERE c = 3</no_use>
                <no_use>WHERE b = 2 AND c = 3</no_use>
            </leftmost_prefix_rule>
            <column_order_strategy>
                <rule priority="1">Equality columns first</rule>
                <rule priority="2">Range columns last</rule>
                <rule priority="3">Most selective first (if all equality)</rule>
            </column_order_strategy>
        </pattern>

        <pattern name="partial">
            <use_case>Index only subset of rows</use_case>
            <benefit>Smaller index, faster updates</benefit>
            <postgresql>CREATE INDEX idx ON users(email) WHERE is_active = true</postgresql>
            <sqlserver>CREATE INDEX idx ON users(email) WHERE is_active = 1</sqlserver>
            <mongodb>db.users.createIndex({email: 1}, {partialFilterExpression: {is_active: true}})</mongodb>
            <examples>
                <example desc="Only active users">WHERE is_active = true</example>
                <example desc="Only pending orders">WHERE status = 'pending'</example>
                <example desc="Non-null values">WHERE phone IS NOT NULL</example>
            </examples>
        </pattern>

        <pattern name="covering">
            <use_case>Include all columns needed by query</use_case>
            <benefit>Index-only scan, no table access</benefit>
            <postgresql>CREATE INDEX idx ON users(email) INCLUDE (name, created_at)</postgresql>
            <sqlserver>CREATE INDEX idx ON users(email) INCLUDE (name, created_at)</sqlserver>
            <oracle>CREATE INDEX idx ON users(email, name, created_at)</oracle>
        </pattern>

        <pattern name="expression">
            <use_case>Index on computed value</use_case>
            <postgresql>CREATE INDEX idx ON users(LOWER(email))</postgresql>
            <mysql>CREATE INDEX idx ON users((LOWER(email)))</mysql>
            <mariadb>CREATE INDEX idx ON users((LOWER(email)))</mariadb>
            <sqlserver>CREATE INDEX idx ON users(email) -- use computed column</sqlserver>
            <oracle>CREATE INDEX idx ON users(LOWER(email))</oracle>
            <mongodb>db.users.createIndex({"$expr": {"$toLower": "$email"}})</mongodb>
        </pattern>

        <pattern name="unique">
            <use_case>Enforce uniqueness</use_case>
            <postgresql>CREATE UNIQUE INDEX idx ON users(email)</postgresql>
            <mysql>CREATE UNIQUE INDEX idx ON users(email)</mysql>
            <mariadb>CREATE UNIQUE INDEX idx ON users(email)</mariadb>
            <sqlite>CREATE UNIQUE INDEX idx ON users(email)</sqlite>
            <sqlserver>CREATE UNIQUE INDEX idx ON users(email)</sqlserver>
            <oracle>CREATE UNIQUE INDEX idx ON users(email)</oracle>
            <mongodb>db.users.createIndex({email: 1}, {unique: true})</mongodb>
        </pattern>

        <pattern name="descending">
            <use_case>ORDER BY DESC queries</use_case>
            <postgresql>CREATE INDEX idx ON posts(created_at DESC)</postgresql>
            <mysql>CREATE INDEX idx ON posts(created_at DESC)</mysql>
            <mariadb>CREATE INDEX idx ON posts(created_at DESC)</mariadb>
            <sqlserver>CREATE INDEX idx ON posts(created_at DESC)</sqlserver>
            <oracle>CREATE INDEX idx ON posts(created_at DESC)</oracle>
            <mongodb>db.posts.createIndex({created_at: -1})</mongodb>
        </pattern>
    </index_patterns>

    <json_indexes>
        <postgresql>
            <gin_all_paths>CREATE INDEX idx ON t USING GIN(data)</gin_all_paths>
            <specific_path>CREATE INDEX idx ON t((data->>'key'))</specific_path>
            <jsonb_path_ops>CREATE INDEX idx ON t USING GIN(data jsonb_path_ops)</jsonb_path_ops>
        </postgresql>
        <mysql>
            <functional>CREATE INDEX idx ON t((CAST(data->>'$.key' AS CHAR(100))))</functional>
        </mysql>
        <mongodb>
            <single_field>db.t.createIndex({"data.key": 1})</single_field>
            <wildcard>db.t.createIndex({"data.$**": 1})</wildcard>
        </mongodb>
    </json_indexes>

    <index_maintenance>
        <find_unused>
            <postgresql>SELECT indexrelname, idx_scan FROM pg_stat_user_indexes WHERE idx_scan = 0</postgresql>
            <mysql>SELECT * FROM sys.schema_unused_indexes</mysql>
            <mongodb>db.t.aggregate([{$indexStats: {}}])</mongodb>
        </find_unused>
        <rebuild>
            <postgresql>REINDEX INDEX idx_name</postgresql>
            <mysql>ALTER TABLE t ENGINE=InnoDB</mysql>
            <mariadb>ALTER TABLE t ENGINE=InnoDB</mariadb>
            <sqlserver>ALTER INDEX idx_name ON t REBUILD</sqlserver>
            <oracle>ALTER INDEX idx_name REBUILD</oracle>
        </rebuild>
        <analyze>
            <postgresql>ANALYZE table_name</postgresql>
            <mysql>ANALYZE TABLE table_name</mysql>
            <sqlserver>UPDATE STATISTICS table_name</sqlserver>
            <oracle>EXEC DBMS_STATS.GATHER_TABLE_STATS('schema','table')</oracle>
        </analyze>
    </index_maintenance>

    <mongodb_specific_indexes>
        <ttl desc="Auto-delete documents">
            <syntax>db.sessions.createIndex({expires_at: 1}, {expireAfterSeconds: 0})</syntax>
        </ttl>
        <text desc="Full-text search">
            <syntax>db.articles.createIndex({title: "text", content: "text"})</syntax>
        </text>
        <geospatial desc="Geographic queries">
            <syntax>db.places.createIndex({location: "2dsphere"})</syntax>
        </geospatial>
        <hashed desc="Sharding">
            <syntax>db.users.createIndex({user_id: "hashed"})</syntax>
        </hashed>
    </mongodb_specific_indexes>

    <redis_indexing>
        <note>Redis uses key patterns and data structures instead of traditional indexes</note>
        <patterns>
            <secondary_index>Use sorted sets: ZADD users:by_email score email</secondary_index>
            <search>Use RediSearch module for full-text search</search>
            <hash_lookup>Use hash key patterns: user:{id}:*</hash_lookup>
        </patterns>
    </redis_indexing>
</indexing>
"""
