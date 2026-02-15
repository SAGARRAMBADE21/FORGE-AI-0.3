"""Normalization principles knowledge base."""
NORMALIZATION_XML = """
<normalization>
    <first_normal_form id="1NF">
        <rule>Atomic values only, no repeating groups</rule>
        <violation>
            <description>Multiple values in single column</description>
            <wrong>
                <sql>CREATE TABLE orders (items VARCHAR(1000)); -- "item1,item2,item3"</sql>
            </wrong>
            <correct>
                <sql>
CREATE TABLE orders (id UUID PRIMARY KEY);
CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    product_id UUID REFERENCES products(id)
);
                </sql>
            </correct>
        </violation>
    </first_normal_form>

    <second_normal_form id="2NF">
        <rule>1NF + no partial dependencies on composite key</rule>
        <violation>
            <description>Non-key column depends on part of composite key</description>
            <wrong>
                <sql>
CREATE TABLE order_items (
    order_id INT,
    product_id INT,
    product_name VARCHAR(100), -- depends only on product_id!
    PRIMARY KEY (order_id, product_id)
);
                </sql>
            </wrong>
            <correct>
                <sql>
CREATE TABLE order_items (
    order_id INT,
    product_id INT REFERENCES products(id),
    unit_price DECIMAL(10,2), -- snapshot at order time (OK)
    PRIMARY KEY (order_id, product_id)
);
CREATE TABLE products (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);
                </sql>
            </correct>
        </violation>
    </second_normal_form>

    <third_normal_form id="3NF">
        <rule>2NF + no transitive dependencies</rule>
        <violation>
            <description>Non-key column depends on another non-key column</description>
            <wrong>
                <sql>
CREATE TABLE employees (
    id INT PRIMARY KEY,
    department_id INT,
    department_name VARCHAR(100), -- depends on department_id!
    department_budget DECIMAL    -- depends on department_id!
);
                </sql>
            </wrong>
            <correct>
                <sql>
CREATE TABLE employees (
    id INT PRIMARY KEY,
    department_id INT REFERENCES departments(id)
);
CREATE TABLE departments (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    budget DECIMAL
);
                </sql>
            </correct>
        </violation>
    </third_normal_form>

    <denormalization_acceptable>
        <case name="read_heavy_counters">
            <description>Avoid COUNT(*) on every read</description>
            <example>
                <sql>
ALTER TABLE posts ADD COLUMN like_count INT DEFAULT 0;
ALTER TABLE posts ADD COLUMN comment_count INT DEFAULT 0;
ALTER TABLE users ADD COLUMN follower_count INT DEFAULT 0;
-- Update via triggers or application
                </sql>
            </example>
            <update_strategy>Trigger, application code, or periodic job</update_strategy>
        </case>

        <case name="snapshot_at_transaction">
            <description>Capture values at point in time</description>
            <example>
                <sql>
CREATE TABLE order_items (
    product_name VARCHAR(100),  -- name at purchase time
    unit_price DECIMAL(10,2)    -- price at purchase time
);
                </sql>
            </example>
            <reason>Historical accuracy, audit trail</reason>
        </case>

        <case name="expensive_calculations">
            <description>Cache computed values</description>
            <example>
                <sql>
ALTER TABLE orders ADD COLUMN total DECIMAL(10,2);
ALTER TABLE products ADD COLUMN average_rating DECIMAL(2,1);
                </sql>
            </example>
            <update_strategy>Calculate on write, not read</update_strategy>
        </case>

        <case name="full_text_search">
            <description>Optimized search column</description>
            <example>
                <postgresql>
ALTER TABLE products ADD COLUMN search_vector TSVECTOR;
UPDATE products SET search_vector = 
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''));
                </postgresql>
            </example>
        </case>

        <case name="materialized_views">
            <description>Pre-computed query results</description>
            <example>
                <postgresql>
CREATE MATERIALIZED VIEW monthly_sales AS
SELECT date_trunc('month', created_at) AS month, SUM(total) AS revenue
FROM orders GROUP BY 1;
                </postgresql>
                <sqlserver>
CREATE VIEW monthly_sales WITH SCHEMABINDING AS
SELECT date_trunc('month', created_at) AS month, SUM(total) AS revenue
FROM dbo.orders GROUP BY date_trunc('month', created_at);
CREATE UNIQUE CLUSTERED INDEX idx ON monthly_sales(month);
                </sqlserver>
            </example>
        </case>
    </denormalization_acceptable>

    <denormalization_antipatterns>
        <antipattern>Storing frequently changing derived data</antipattern>
        <antipattern>Duplicating without update mechanism</antipattern>
        <antipattern>Premature optimization before measuring</antipattern>
        <antipattern>Comma-separated values instead of junction tables</antipattern>
    </denormalization_antipatterns>
</normalization>
"""
