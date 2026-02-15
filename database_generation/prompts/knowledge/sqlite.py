SQLITE_XML = """
<sqlite>
    <info>
        <name>SQLite</name>
        <type>Lightweight embedded database</type>
        <features>Serverless, zero-config, single file, cross-platform</features>
        <use_cases>Mobile apps, desktop apps, embedded systems, testing, small websites</use_cases>
    </info>

    <characteristics>
        <serverless>No separate server process</serverless>
        <single_file>Entire database in one file</single_file>
        <zero_config>No setup or administration</zero_config>
        <cross_platform>Works on all platforms</cross_platform>
        <size_limit>Up to 281 TB</size_limit>
    </characteristics>

    <data_types>
        <type name="NULL">Null value</type>
        <type name="INTEGER">Signed integer (1, 2, 3, 4, 6, or 8 bytes)</type>
        <type name="REAL">8-byte floating point</type>
        <type name="TEXT">UTF-8 or UTF-16 string</type>
        <type name="BLOB">Binary data</type>
        <note>SQLite uses type affinity, not strict types</note>
        <type_affinity>
            <affinity name="INTEGER">INT, INTEGER, TINYINT, SMALLINT, BIGINT</affinity>
            <affinity name="TEXT">CHAR, VARCHAR, TEXT, CLOB</affinity>
            <affinity name="REAL">REAL, DOUBLE, FLOAT</affinity>
            <affinity name="NUMERIC">DECIMAL, BOOLEAN, DATE, DATETIME</affinity>
        </type_affinity>
    </data_types>

    <uuid_handling>
        <storage>TEXT (36 chars) or BLOB (16 bytes)</storage>
        <generate>Use application or extension (uuid-ossp)</generate>
        <example>
CREATE TABLE users (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email TEXT UNIQUE NOT NULL
);
        </example>
    </uuid_handling>

    <auto_increment>
        <syntax>INTEGER PRIMARY KEY AUTOINCREMENT</syntax>
        <note>AUTOINCREMENT prevents reuse of rowid</note>
        <example>
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL
);
        </example>
    </auto_increment>

    <indexes>
        <create>CREATE INDEX idx_users_email ON users(email)</create>
        <unique>CREATE UNIQUE INDEX idx_users_email ON users(email)</unique>
        <partial>CREATE INDEX idx_active ON users(email) WHERE is_active = 1</partial>
        <expression>CREATE INDEX idx_lower ON users(lower(email))</expression>
    </indexes>

    <constraints>
        <primary_key>PRIMARY KEY</primary_key>
        <not_null>NOT NULL</not_null>
        <unique>UNIQUE</unique>
        <check>CHECK (price > 0)</check>
        <default>DEFAULT value</default>
        <foreign_key>
            <enable>PRAGMA foreign_keys = ON</enable>
            <note>Foreign keys disabled by default!</note>
            <syntax>REFERENCES table(column) ON DELETE CASCADE</syntax>
        </foreign_key>
    </constraints>

    <json_support version="3.9+">
        <functions>
            <func>json(value)</func>
            <func>json_extract(json, path)</func>
            <func>json_insert(json, path, value)</func>
            <func>json_replace(json, path, value)</func>
            <func>json_set(json, path, value)</func>
            <func>json_remove(json, path)</func>
            <func>json_type(json)</func>
            <func>json_array(values...)</func>
            <func>json_object(key, value...)</func>
        </functions>
        <operators>
            <op>json_extract(data, '$.key')</op>
            <op>data ->> '$.key'</op>
        </operators>
    </json_support>

    <common_operations>
        <upsert>
            <sql>
INSERT INTO users (email, name) VALUES ('a@b.com', 'A')
ON CONFLICT(email) DO UPDATE SET name = excluded.name;
            </sql>
        </upsert>
        <returning>INSERT INTO users (email) VALUES ('a@b.com') RETURNING id</returning>
        <last_insert>SELECT last_insert_rowid()</last_insert>
    </common_operations>

    <pragmas>
        <pragma name="foreign_keys">PRAGMA foreign_keys = ON</pragma>
        <pragma name="journal_mode">PRAGMA journal_mode = WAL</pragma>
        <pragma name="synchronous">PRAGMA synchronous = NORMAL</pragma>
        <pragma name="cache_size">PRAGMA cache_size = -64000</pragma>
        <pragma name="busy_timeout">PRAGMA busy_timeout = 5000</pragma>
    </pragmas>

    <limitations>
        <limitation>Single writer at a time</limitation>
        <limitation>No user management/permissions</limitation>
        <limitation>No stored procedures</limitation>
        <limitation>Limited ALTER TABLE support</limitation>
        <limitation>No RIGHT/FULL OUTER JOIN</limitation>
    </limitations>
</sqlite>
"""
