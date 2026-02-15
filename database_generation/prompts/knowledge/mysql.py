"""MySQL-specific knowledge base."""
MYSQL_XML = """
<mysql>
    <info>
        <name>MySQL</name>
        <type>Popular open-source relational database</type>
        <features>JSON support, fulltext search, replication, partitioning</features>
        <default_engine>InnoDB</default_engine>
    </info>

    <version_features>
        <feature version="5.7">JSON data type, generated columns</feature>
        <feature version="8.0">CTEs, window functions, CHECK constraints (enforced)</feature>
        <feature version="8.0.13">Functional indexes</feature>
        <feature version="8.0.16">CHECK constraints enforced</feature>
    </version_features>

    <data_types>
        <uuid>
            <storage>CHAR(36) or BINARY(16)</storage>
            <generate>UUID()</generate>
            <binary_convert>UUID_TO_BIN(UUID(), 1)</binary_convert>
            <string_convert>BIN_TO_UUID(binary, 1)</string_convert>
        </uuid>
        <auto_increment>INT AUTO_INCREMENT PRIMARY KEY</auto_increment>
        <json>
            <operators>
                <op name="->" desc="Get JSON">data->'$.key'</op>
                <op name="->>" desc="Get text">data->>'$.key'</op>
            </operators>
            <functions>
                <func>JSON_EXTRACT(data, '$.key')</func>
                <func>JSON_SET(data, '$.key', val)</func>
                <func>JSON_INSERT(data, '$.key', val)</func>
                <func>JSON_REMOVE(data, '$.key')</func>
                <func>JSON_CONTAINS(data, '"val"', '$.arr')</func>
                <func>JSON_MERGE_PATCH(data1, data2)</func>
            </functions>
        </json>
        <generated_columns>
            <virtual>col AS (expression) VIRTUAL</virtual>
            <stored>col AS (expression) STORED</stored>
        </generated_columns>
    </data_types>

    <indexes>
        <btree>CREATE INDEX idx ON t(col)</btree>
        <fulltext>CREATE FULLTEXT INDEX idx ON t(title, content)</fulltext>
        <spatial>CREATE SPATIAL INDEX idx ON t(location)</spatial>
        <functional>CREATE INDEX idx ON t((LOWER(email)))</functional>
        <invisible>ALTER TABLE t ALTER INDEX idx INVISIBLE</invisible>
    </indexes>

    <fulltext_search>
        <natural>
            <sql>SELECT * FROM articles WHERE MATCH(title, content) AGAINST('keyword')</sql>
        </natural>
        <boolean>
            <sql>SELECT * FROM articles WHERE MATCH(title, content) AGAINST('+required -excluded' IN BOOLEAN MODE)</sql>
        </boolean>
    </fulltext_search>

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

    <partitioning>
        <range>
            <sql>
CREATE TABLE orders (
    id INT NOT NULL, created_at DATETIME NOT NULL,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
            </sql>
        </range>
        <list>
            <sql>
CREATE TABLE users (id INT NOT NULL, region VARCHAR(10) NOT NULL, PRIMARY KEY (id, region))
PARTITION BY LIST COLUMNS(region) (
    PARTITION p_us VALUES IN ('us-east', 'us-west'),
    PARTITION p_eu VALUES IN ('eu-west', 'eu-central')
);
            </sql>
        </list>
    </partitioning>

    <common_operations>
        <upsert>
            <sql>
INSERT INTO users (email, name) VALUES ('a@b.com', 'A')
ON DUPLICATE KEY UPDATE name = VALUES(name), updated_at = NOW();
            </sql>
        </upsert>
        <replace>REPLACE INTO settings (user_id, theme) VALUES (1, 'dark')</replace>
        <last_insert_id>SELECT LAST_INSERT_ID()</last_insert_id>
    </common_operations>

    <configuration>
        <important>
            <setting name="innodb_buffer_pool_size">70% of RAM</setting>
            <setting name="max_connections">150</setting>
            <setting name="character_set_server">utf8mb4</setting>
            <setting name="collation_server">utf8mb4_unicode_ci</setting>
        </important>
        <table_defaults>ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci</table_defaults>
    </configuration>
</mysql>
"""
