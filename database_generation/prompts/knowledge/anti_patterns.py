"""Common anti-patterns knowledge base."""
ANTI_PATTERNS_XML = """
<anti_patterns>
    <schema_antipatterns>
        <antipattern name="god_table">
            <description>Everything in one table with type column</description>
            <wrong>
CREATE TABLE everything (
    id INT, type VARCHAR(50),
    data JSON
);
            </wrong>
            <correct>
CREATE TABLE users (...);
CREATE TABLE products (...);
CREATE TABLE orders (...);
            </correct>
        </antipattern>

        <antipattern name="eav">
            <description>Entity-Attribute-Value pattern</description>
            <wrong>
CREATE TABLE attributes (
    entity_id INT,
    attribute_name VARCHAR(100),
    attribute_value TEXT
);
            </wrong>
            <correct>
CREATE TABLE products (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL(10,2),
    metadata JSONB  -- for truly dynamic data
);
            </correct>
            <problems>No type safety, no constraints, terrible performance</problems>
        </antipattern>

        <antipattern name="comma_separated">
            <description>Multiple values in one column</description>
            <wrong>
CREATE TABLE users (id INT, tags VARCHAR(1000)); -- "admin,manager,sales"
            </wrong>
            <correct>
CREATE TABLE user_tags (
    user_id INT REFERENCES users(id),
    tag_id INT REFERENCES tags(id),
    PRIMARY KEY (user_id, tag_id)
);
            </correct>
        </antipattern>

        <antipattern name="missing_primary_key">
            <description>Table without primary key</description>
            <wrong>CREATE TABLE logs (message TEXT, created_at TIMESTAMP);</wrong>
            <correct>
CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
            </correct>
        </antipattern>

        <antipattern name="natural_key_as_pk">
            <description>Using business value as primary key</description>
            <wrong>
CREATE TABLE users (email VARCHAR(255) PRIMARY KEY, name VARCHAR(100));
            </wrong>
            <correct>
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100)
);
            </correct>
            <reason>Email can change, causing cascading updates</reason>
        </antipattern>
    </schema_antipatterns>

    <datatype_antipatterns>
        <antipattern name="float_for_money">
            <description>Using floating point for financial data</description>
            <wrong>CREATE TABLE products (price FLOAT);</wrong>
            <correct>CREATE TABLE products (price NUMERIC(10,2));</correct>
            <reason>0.1 + 0.2 = 0.30000000000000004 in float</reason>
        </antipattern>

        <antipattern name="string_for_everything">
            <description>Using VARCHAR for all data types</description>
            <wrong>
CREATE TABLE orders (
    user_id VARCHAR(100),
    total VARCHAR(50),
    is_paid VARCHAR(10),
    created_at VARCHAR(50)
);
            </wrong>
            <correct>
CREATE TABLE orders (
    user_id UUID REFERENCES users(id),
    total NUMERIC(10,2),
    is_paid BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
            </correct>
        </antipattern>

        <antipattern name="timestamp_without_timezone">
            <description>Ambiguous timestamps</description>
            <wrong>created_at TIMESTAMP</wrong>
            <correct>created_at TIMESTAMPTZ DEFAULT NOW()</correct>
        </antipattern>
    </datatype_antipatterns>

    <index_antipatterns>
        <antipattern name="missing_fk_index">
            <description>Foreign key without index</description>
            <wrong>user_id UUID REFERENCES users(id) -- no index!</wrong>
            <correct>
user_id UUID REFERENCES users(id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
            </correct>
            <impact>Extremely slow JOINs and ON DELETE CASCADE</impact>
        </antipattern>

        <antipattern name="over_indexing">
            <description>Too many indexes</description>
            <wrong>Index on every column</wrong>
            <correct>Only index queried columns</correct>
            <impact>Slows down writes significantly</impact>
        </antipattern>

        <antipattern name="wrong_composite_order">
            <description>Wrong column order in composite index</description>
            <wrong>CREATE INDEX idx ON orders(status, user_id); -- status has few values</wrong>
            <correct>CREATE INDEX idx ON orders(user_id, status); -- high cardinality first</correct>
        </antipattern>
    </index_antipatterns>

    <query_antipatterns>
        <antipattern name="select_star">
            <wrong>SELECT * FROM users WHERE id = $1</wrong>
            <correct>SELECT id, email, name FROM users WHERE id = $1</correct>
        </antipattern>

        <antipattern name="n_plus_one">
            <description>Query in a loop</description>
            <wrong>
users = query("SELECT * FROM users")
for user in users:
    orders = query(f"SELECT * FROM orders WHERE user_id = {user.id}")
            </wrong>
            <correct>
query("SELECT u.*, o.* FROM users u LEFT JOIN orders o ON u.id = o.user_id")
            </correct>
        </antipattern>

        <antipattern name="offset_pagination">
            <description>OFFSET for deep pagination</description>
            <wrong>SELECT * FROM posts ORDER BY created_at OFFSET 10000 LIMIT 20</wrong>
            <correct>SELECT * FROM posts WHERE created_at &lt; $cursor ORDER BY created_at DESC LIMIT 20</correct>
            <reason>OFFSET scans all skipped rows</reason>
        </antipattern>
    </query_antipatterns>

    <relationship_antipatterns>
        <antipattern name="missing_on_delete">
            <description>Foreign key without action</description>
            <wrong>user_id UUID REFERENCES users(id)</wrong>
            <correct>user_id UUID REFERENCES users(id) ON DELETE CASCADE</correct>
        </antipattern>

        <antipattern name="circular_dependency">
            <description>Tables referencing each other</description>
            <wrong>
users.current_order_id REFERENCES orders(id)
orders.user_id REFERENCES users(id)
-- Cannot insert anything!
            </wrong>
            <correct>Break cycle with nullable FK or use flag column instead</correct>
        </antipattern>
    </relationship_antipatterns>

    <naming_antipatterns>
        <antipattern name="inconsistent_naming">
            <wrong>User, order_items, ProductCategories</wrong>
            <correct>users, order_items, product_categories</correct>
        </antipattern>

        <antipattern name="reserved_words">
            <wrong>order, user, table, index</wrong>
            <correct>orders, users, tables, indexes</correct>
        </antipattern>
    </naming_antipatterns>

    <golden_rules>
        <do>Use surrogate keys (UUID)</do>
        <do>Use appropriate data types</do>
        <do>Index foreign keys</do>
        <do>Use parameterized queries</do>
        <do>Be consistent with naming</do>
        <do>Document your schema</do>
        <dont>Store multiple values in one column</dont>
        <dont>Use FLOAT for money</dont>
        <dont>Use SELECT *</dont>
        <dont>Skip primary keys</dont>
        <dont>Over-index</dont>
        <dont>Store passwords in plain text</dont>
    </golden_rules>
</anti_patterns>
"""
