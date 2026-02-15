"""PostgreSQL-specific knowledge base."""
POSTGRESQL_XML = """
<postgresql>
    <info>
        <name>PostgreSQL</name>
        <type>Open-source advanced relational database</type>
        <features>JSONB, GIN indexes, full-text search, partitioning, CTEs, window functions</features>
    </info>

    <version_features>
        <feature version="9.4">JSONB data type</feature>
        <feature version="9.5">UPSERT (ON CONFLICT)</feature>
        <feature version="9.6">Parallel queries</feature>
        <feature version="10">Native partitioning, logical replication</feature>
        <feature version="11">Stored procedures, JIT compilation</feature>
        <feature version="12">Generated columns</feature>
        <feature version="14">JSONB subscripting</feature>
        <feature version="15">MERGE statement</feature>
    </version_features>

    <data_types>
        <uuid>
            <extension>CREATE EXTENSION IF NOT EXISTS "pgcrypto";</extension>
            <generate>gen_random_uuid()</generate>
            <declaration>id UUID DEFAULT gen_random_uuid() PRIMARY KEY</declaration>
        </uuid>
        <serial>
            <types>SERIAL, BIGSERIAL, GENERATED ALWAYS AS IDENTITY</types>
            <preferred>GENERATED ALWAYS AS IDENTITY</preferred>
        </serial>
        <jsonb>
            <operators>
                <op name="->" desc="Get JSON value">data->'key'</op>
                <op name="->>" desc="Get as text">data->>'key'</op>
                <op name="#>" desc="Path to JSON">data#>'{a,b}'</op>
                <op name="#>>" desc="Path to text">data#>>'{a,b}'</op>
                <op name="@>" desc="Contains">data @> '{"k":"v"}'</op>
                <op name="?" desc="Has key">data ? 'key'</op>
                <op name="?|" desc="Has any key">data ?| array['a','b']</op>
                <op name="?&amp;" desc="Has all keys">data ?&amp; array['a','b']</op>
            </operators>
            <functions>
                <func>jsonb_set(data, '{key}', '"value"')</func>
                <func>data || '{"new":"val"}'::jsonb</func>
                <func>data - 'key'</func>
                <func>jsonb_strip_nulls(data)</func>
                <func>jsonb_pretty(data)</func>
                <func>jsonb_typeof(data)</func>
            </functions>
        </jsonb>
        <arrays>
            <declaration>tags TEXT[] DEFAULT '{}'</declaration>
            <functions>
                <func>array_append(arr, 'new')</func>
                <func>array_remove(arr, 'old')</func>
                <func>array_cat(arr1, arr2)</func>
                <func>unnest(arr)</func>
                <func>array_agg(col)</func>
            </functions>
            <operators>
                <op>'value' = ANY(arr)</op>
                <op>arr @> ARRAY['a','b']</op>
                <op>arr &amp;&amp; ARRAY['a','b']</op>
            </operators>
        </arrays>
        <range_types>
            <types>INT4RANGE, INT8RANGE, NUMRANGE, TSRANGE, TSTZRANGE, DATERANGE</types>
            <operators>
                <op>range @> value</op>
                <op>range1 &amp;&amp; range2</op>
                <op>range1 -|- range2</op>
            </operators>
        </range_types>
    </data_types>

    <indexes>
        <gin>
            <jsonb>CREATE INDEX idx ON t USING GIN(data)</jsonb>
            <jsonb_path>CREATE INDEX idx ON t USING GIN(data jsonb_path_ops)</jsonb_path>
            <array>CREATE INDEX idx ON t USING GIN(tags)</array>
            <fulltext>CREATE INDEX idx ON t USING GIN(to_tsvector('english', content))</fulltext>
            <trigram>CREATE INDEX idx ON t USING GIN(name gin_trgm_ops)</trigram>
        </gin>
        <gist>
            <geometric>CREATE INDEX idx ON t USING GIST(location)</geometric>
            <range>CREATE INDEX idx ON t USING GIST(period)</range>
            <exclusion>
                <extension>CREATE EXTENSION btree_gist</extension>
                <constraint>EXCLUDE USING GIST (room WITH =, period WITH &amp;&amp;)</constraint>
            </exclusion>
        </gist>
        <brin>
            <use_case>Large tables with natural ordering</use_case>
            <syntax>CREATE INDEX idx ON logs USING BRIN(created_at)</syntax>
        </brin>
        <partial>CREATE INDEX idx ON users(email) WHERE is_active = true</partial>
        <expression>CREATE INDEX idx ON users(LOWER(email))</expression>
        <covering>CREATE INDEX idx ON users(email) INCLUDE (name, created_at)</covering>
    </indexes>

    <constraints>
        <check>ALTER TABLE products ADD CONSTRAINT chk CHECK (price > 0)</check>
        <exclusion>
            <sql>
CREATE EXTENSION btree_gist;
ALTER TABLE reservations ADD CONSTRAINT no_overlap
EXCLUDE USING GIST (room_id WITH =, during WITH &amp;&amp;);
            </sql>
        </exclusion>
        <domain>
            <sql>
CREATE DOMAIN email AS VARCHAR(255) 
CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
            </sql>
        </domain>
    </constraints>

    <triggers>
        <updated_at>
            <sql>
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_updated BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
            </sql>
        </updated_at>
    </triggers>

    <partitioning>
        <range>
            <sql>
CREATE TABLE orders (id UUID, created_at TIMESTAMPTZ NOT NULL)
PARTITION BY RANGE (created_at);

CREATE TABLE orders_2024_q1 PARTITION OF orders
FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
            </sql>
        </range>
        <list>
            <sql>
CREATE TABLE users (id UUID, region VARCHAR(10))
PARTITION BY LIST (region);

CREATE TABLE users_us PARTITION OF users FOR VALUES IN ('us-east', 'us-west');
            </sql>
        </list>
        <hash>
            <sql>
CREATE TABLE sessions (id UUID, user_id UUID)
PARTITION BY HASH (user_id);

CREATE TABLE sessions_0 PARTITION OF sessions FOR VALUES WITH (MODULUS 4, REMAINDER 0);
            </sql>
        </hash>
    </partitioning>

    <row_level_security>
        <enable>ALTER TABLE docs ENABLE ROW LEVEL SECURITY</enable>
        <policy>CREATE POLICY user_policy ON docs USING (user_id = current_setting('app.user_id')::UUID)</policy>
        <set_context>SET app.user_id = 'uuid-here'</set_context>
    </row_level_security>

    <common_operations>
        <upsert>
            <sql>
INSERT INTO users (email, name) VALUES ('a@b.com', 'A')
ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, updated_at = NOW();
            </sql>
        </upsert>
        <returning>
            <insert>INSERT INTO orders (total) VALUES (99.99) RETURNING id, created_at</insert>
            <update>UPDATE users SET status = 'active' RETURNING *</update>
            <delete>DELETE FROM sessions WHERE expires &lt; NOW() RETURNING id</delete>
        </returning>
        <cte>
            <sql>
WITH active AS (SELECT * FROM users WHERE is_active)
SELECT * FROM active WHERE created_at > '2024-01-01';
            </sql>
        </cte>
        <window_functions>
            <sql>
SELECT user_id, SUM(total), RANK() OVER (ORDER BY SUM(total) DESC)
FROM orders GROUP BY user_id;
            </sql>
        </window_functions>
    </common_operations>
</postgresql>
"""
