MARIADB_XML = """
<mariadb>
    <info>
        <name>MariaDB</name>
        <type>MySQL fork with enhanced features</type>
        <features>Galera cluster, columnstore, temporal tables, JSON, sequences</features>
        <compatibility>Drop-in replacement for MySQL</compatibility>
    </info>

    <unique_features>
        <feature name="sequences">Native SEQUENCE support (like Oracle/PostgreSQL)</feature>
        <feature name="temporal_tables">System-versioned tables for history</feature>
        <feature name="columnstore">MariaDB ColumnStore for analytics</feature>
        <feature name="galera">Synchronous multi-master replication</feature>
        <feature name="oracle_mode">SET SQL_MODE='ORACLE' for compatibility</feature>
    </unique_features>

    <data_types>
        <uuid>
            <type>UUID (native in 10.7+) or CHAR(36)</type>
            <generate>UUID()</generate>
            <example>id UUID DEFAULT UUID() PRIMARY KEY</example>
        </uuid>
        <auto_increment>INT AUTO_INCREMENT PRIMARY KEY</auto_increment>
        <sequence>
            <sql>
CREATE SEQUENCE user_seq START WITH 1 INCREMENT BY 1;
SELECT NEXT VALUE FOR user_seq;
            </sql>
        </sequence>
        <json>
            <type>JSON (alias for LONGTEXT with validation)</type>
            <functions>Same as MySQL JSON functions</functions>
        </json>
    </data_types>

    <temporal_tables>
        <create>
            <sql>
CREATE TABLE products (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL(10,2),
    valid_from TIMESTAMP(6) GENERATED ALWAYS AS ROW START,
    valid_to TIMESTAMP(6) GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME (valid_from, valid_to)
) WITH SYSTEM VERSIONING;
            </sql>
        </create>
        <query>
            <current>SELECT * FROM products</current>
            <history>SELECT * FROM products FOR SYSTEM_TIME ALL</history>
            <point_in_time>SELECT * FROM products FOR SYSTEM_TIME AS OF '2024-01-01'</point_in_time>
            <range>SELECT * FROM products FOR SYSTEM_TIME FROM '2024-01-01' TO '2024-06-01'</range>
        </query>
    </temporal_tables>

    <indexes>
        <btree>CREATE INDEX idx ON t(col)</btree>
        <fulltext>CREATE FULLTEXT INDEX idx ON t(col)</fulltext>
        <spatial>CREATE SPATIAL INDEX idx ON t(col)</spatial>
        <hash>CREATE INDEX idx USING HASH ON t(col)</hash>
    </indexes>

    <json_support>
        <operators>
            <op>data->'$.key'</op>
            <op>data->>'$.key'</op>
        </operators>
        <functions>
            <func>JSON_EXTRACT(data, '$.key')</func>
            <func>JSON_SET(data, '$.key', value)</func>
            <func>JSON_INSERT(data, '$.key', value)</func>
            <func>JSON_REMOVE(data, '$.key')</func>
            <func>JSON_CONTAINS(data, value, '$.path')</func>
            <func>JSON_ARRAY(values...)</func>
            <func>JSON_OBJECT(key, value...)</func>
        </functions>
    </json_support>

    <triggers>
        <updated_at>
            <sql>
DELIMITER //
CREATE TRIGGER before_update BEFORE UPDATE ON users
FOR EACH ROW BEGIN
    SET NEW.updated_at = NOW();
END//
DELIMITER ;
            </sql>
        </updated_at>
    </triggers>

    <common_operations>
        <upsert>
            <sql>
INSERT INTO users (email, name) VALUES ('a@b.com', 'A')
ON DUPLICATE KEY UPDATE name = VALUES(name);
            </sql>
        </upsert>
        <replace>REPLACE INTO users (id, email, name) VALUES (1, 'a@b.com', 'A')</replace>
        <returning version="10.5+">
            <sql>INSERT INTO users (email) VALUES ('a@b.com') RETURNING id</sql>
        </returning>
    </common_operations>

    <partitioning>
        <range>
            <sql>
CREATE TABLE orders (id INT, created_at DATE)
PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025)
);
            </sql>
        </range>
        <system_versioned>
            <sql>
CREATE TABLE products (...) WITH SYSTEM VERSIONING
PARTITION BY SYSTEM_TIME (
    PARTITION p_hist HISTORY,
    PARTITION p_curr CURRENT
);
            </sql>
        </system_versioned>
    </partitioning>

    <galera_cluster>
        <description>Synchronous multi-master replication</description>
        <benefits>High availability, automatic failover, read scaling</benefits>
        <constraints>All tables must have primary key, no XA transactions</constraints>
    </galera_cluster>
</mariadb>
"""
