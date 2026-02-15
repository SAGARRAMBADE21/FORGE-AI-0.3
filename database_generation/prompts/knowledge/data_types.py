"""Data types knowledge base."""
DATA_TYPES_XML = """
<data_types>
    <identifiers>
        <type name="uuid" use_case="Primary key (distributed)">
            <postgresql>UUID</postgresql>
            <mysql>CHAR(36) or BINARY(16)</mysql>
            <mariadb>UUID or CHAR(36)</mariadb>
            <sqlite>TEXT</sqlite>
            <sqlserver>UNIQUEIDENTIFIER</sqlserver>
            <oracle>RAW(16) or VARCHAR2(36)</oracle>
            <mongodb>UUID() or ObjectId</mongodb>
            <redis>string</redis>
            <generation>
                <postgresql>gen_random_uuid()</postgresql>
                <mysql>UUID()</mysql>
                <mariadb>UUID()</mariadb>
                <sqlserver>NEWID()</sqlserver>
                <oracle>SYS_GUID()</oracle>
            </generation>
        </type>
        <type name="auto_increment" use_case="Primary key (single node)">
            <postgresql>SERIAL or BIGSERIAL or GENERATED ALWAYS AS IDENTITY</postgresql>
            <mysql>INT AUTO_INCREMENT</mysql>
            <mariadb>INT AUTO_INCREMENT</mariadb>
            <sqlite>INTEGER PRIMARY KEY AUTOINCREMENT</sqlite>
            <sqlserver>INT IDENTITY(1,1)</sqlserver>
            <oracle>NUMBER GENERATED ALWAYS AS IDENTITY</oracle>
            <mongodb>ObjectId (automatic)</mongodb>
        </type>
    </identifiers>

    <strings>
        <type name="short_string" max_length="255">
            <use_cases>username, email, name, title, slug, phone, url</use_cases>
            <postgresql>VARCHAR(n)</postgresql>
            <mysql>VARCHAR(n)</mysql>
            <mariadb>VARCHAR(n)</mariadb>
            <sqlite>TEXT</sqlite>
            <sqlserver>NVARCHAR(n)</sqlserver>
            <oracle>VARCHAR2(n)</oracle>
            <mongodb>String</mongodb>
            <redis>string</redis>
        </type>
        <type name="long_text" max_length="unlimited">
            <use_cases>description, content, body, bio, notes</use_cases>
            <postgresql>TEXT</postgresql>
            <mysql>TEXT or LONGTEXT</mysql>
            <mariadb>TEXT or LONGTEXT</mariadb>
            <sqlite>TEXT</sqlite>
            <sqlserver>NVARCHAR(MAX)</sqlserver>
            <oracle>CLOB</oracle>
            <mongodb>String</mongodb>
            <redis>string</redis>
        </type>
        <type name="fixed_string">
            <use_cases>country_code, currency_code, locale</use_cases>
            <postgresql>CHAR(n)</postgresql>
            <mysql>CHAR(n)</mysql>
            <mariadb>CHAR(n)</mariadb>
            <sqlite>TEXT</sqlite>
            <sqlserver>NCHAR(n)</sqlserver>
            <oracle>CHAR(n)</oracle>
        </type>
        <size_guidelines>
            <field name="username" size="30"/>
            <field name="email" size="255"/>
            <field name="first_name" size="50"/>
            <field name="last_name" size="50"/>
            <field name="full_name" size="100"/>
            <field name="title" size="255"/>
            <field name="slug" size="100"/>
            <field name="phone" size="20"/>
            <field name="url" size="2048"/>
            <field name="password_hash" size="255"/>
            <field name="short_description" size="500"/>
            <field name="country_code" size="2"/>
            <field name="currency_code" size="3"/>
            <field name="locale" size="10"/>
        </size_guidelines>
    </strings>

    <numbers>
        <type name="small_integer" range="-32768 to 32767">
            <use_cases>age, rating, small counts, year</use_cases>
            <postgresql>SMALLINT</postgresql>
            <mysql>SMALLINT</mysql>
            <mariadb>SMALLINT</mariadb>
            <sqlite>INTEGER</sqlite>
            <sqlserver>SMALLINT</sqlserver>
            <oracle>NUMBER(5)</oracle>
            <mongodb>NumberInt</mongodb>
            <redis>string (INCR/DECR)</redis>
        </type>
        <type name="integer" range="-2B to 2B">
            <use_cases>counts, quantities, IDs</use_cases>
            <postgresql>INTEGER</postgresql>
            <mysql>INT</mysql>
            <mariadb>INT</mariadb>
            <sqlite>INTEGER</sqlite>
            <sqlserver>INT</sqlserver>
            <oracle>NUMBER(10)</oracle>
            <mongodb>NumberInt</mongodb>
            <redis>string (INCR/DECR)</redis>
        </type>
        <type name="big_integer" range="-9 quintillion to 9 quintillion">
            <use_cases>large counts, timestamps as numbers</use_cases>
            <postgresql>BIGINT</postgresql>
            <mysql>BIGINT</mysql>
            <mariadb>BIGINT</mariadb>
            <sqlite>INTEGER</sqlite>
            <sqlserver>BIGINT</sqlserver>
            <oracle>NUMBER(19)</oracle>
            <mongodb>NumberLong</mongodb>
            <redis>string</redis>
        </type>
        <type name="decimal" precision="exact">
            <use_cases>money, prices, financial calculations</use_cases>
            <critical>NEVER use FLOAT/DOUBLE for money</critical>
            <postgresql>NUMERIC(p,s) or DECIMAL(p,s)</postgresql>
            <mysql>DECIMAL(p,s)</mysql>
            <mariadb>DECIMAL(p,s)</mariadb>
            <sqlite>REAL or TEXT</sqlite>
            <sqlserver>DECIMAL(p,s) or MONEY</sqlserver>
            <oracle>NUMBER(p,s)</oracle>
            <mongodb>Decimal128</mongodb>
            <redis>string</redis>
            <common_precisions>
                <money precision="10" scale="2">Up to 99,999,999.99</money>
                <large_money precision="19" scale="4">Financial precision</large_money>
                <percentage precision="5" scale="2">0.00 to 100.00</percentage>
                <rate precision="10" scale="6">High precision rates</rate>
            </common_precisions>
        </type>
        <type name="float" precision="approximate">
            <use_cases>scientific calculations, non-financial</use_cases>
            <warning>NOT for money or exact calculations</warning>
            <postgresql>DOUBLE PRECISION or REAL</postgresql>
            <mysql>DOUBLE or FLOAT</mysql>
            <mariadb>DOUBLE or FLOAT</mariadb>
            <sqlite>REAL</sqlite>
            <sqlserver>FLOAT or REAL</sqlserver>
            <oracle>BINARY_DOUBLE or BINARY_FLOAT</oracle>
            <mongodb>Double</mongodb>
        </type>
        <type name="coordinates">
            <latitude precision="10" scale="8" range="-90 to 90"/>
            <longitude precision="11" scale="8" range="-180 to 180"/>
        </type>
    </numbers>

    <boolean>
        <postgresql>BOOLEAN</postgresql>
        <mysql>TINYINT(1) or BOOLEAN</mysql>
        <mariadb>TINYINT(1) or BOOLEAN</mariadb>
        <sqlite>INTEGER (0/1)</sqlite>
        <sqlserver>BIT</sqlserver>
        <oracle>NUMBER(1) or CHAR(1)</oracle>
        <mongodb>Boolean</mongodb>
        <redis>string ("0"/"1" or "true"/"false")</redis>
        <naming_convention>is_active, is_verified, has_permission, can_edit</naming_convention>
    </boolean>

    <datetime>
        <type name="date_only">
            <use_cases>birth_date, start_date, end_date</use_cases>
            <postgresql>DATE</postgresql>
            <mysql>DATE</mysql>
            <mariadb>DATE</mariadb>
            <sqlite>TEXT (ISO format)</sqlite>
            <sqlserver>DATE</sqlserver>
            <oracle>DATE</oracle>
            <mongodb>ISODate</mongodb>
            <redis>string (ISO format)</redis>
        </type>
        <type name="time_only">
            <use_cases>open_time, close_time</use_cases>
            <postgresql>TIME or TIME WITH TIME ZONE</postgresql>
            <mysql>TIME</mysql>
            <mariadb>TIME</mariadb>
            <sqlite>TEXT</sqlite>
            <sqlserver>TIME</sqlserver>
            <oracle>TIMESTAMP</oracle>
        </type>
        <type name="timestamp">
            <use_cases>created_at, updated_at, event times</use_cases>
            <critical>ALWAYS store in UTC</critical>
            <postgresql>TIMESTAMPTZ (preferred) or TIMESTAMP</postgresql>
            <mysql>TIMESTAMP or DATETIME</mysql>
            <mariadb>TIMESTAMP or DATETIME</mariadb>
            <sqlite>TEXT (ISO format)</sqlite>
            <sqlserver>DATETIME2 or DATETIMEOFFSET</sqlserver>
            <oracle>TIMESTAMP WITH TIME ZONE</oracle>
            <mongodb>ISODate</mongodb>
            <redis>string (ISO or Unix timestamp)</redis>
            <best_practice>Convert to local time in application layer</best_practice>
        </type>
    </datetime>

    <json>
        <use_cases>metadata, settings, flexible attributes, API responses</use_cases>
        <postgresql>JSONB (preferred) or JSON</postgresql>
        <mysql>JSON</mysql>
        <mariadb>JSON (alias for LONGTEXT)</mariadb>
        <sqlite>TEXT</sqlite>
        <sqlserver>NVARCHAR(MAX)</sqlserver>
        <oracle>JSON (21c+) or CLOB</oracle>
        <mongodb>Object (native)</mongodb>
        <redis>string (JSON.stringify) or RedisJSON module</redis>
        <when_to_use>
            <yes>Flexible metadata, user settings, varying attributes</yes>
            <no>Frequently queried fields, relationships, core business data</no>
        </when_to_use>
    </json>

    <binary>
        <postgresql>BYTEA</postgresql>
        <mysql>BLOB, MEDIUMBLOB, LONGBLOB</mysql>
        <mariadb>BLOB, MEDIUMBLOB, LONGBLOB</mariadb>
        <sqlite>BLOB</sqlite>
        <sqlserver>VARBINARY(MAX)</sqlserver>
        <oracle>BLOB</oracle>
        <mongodb>BinData</mongodb>
        <best_practice>Store files in object storage (S3), save URL in database</best_practice>
    </binary>

    <arrays>
        <postgresql>TYPE[] (native arrays)</postgresql>
        <mysql>JSON</mysql>
        <mariadb>JSON</mariadb>
        <sqlite>TEXT (JSON)</sqlite>
        <sqlserver>JSON or separate table</sqlserver>
        <oracle>VARRAY or nested table</oracle>
        <mongodb>Array (native)</mongodb>
        <redis>List or Set</redis>
    </arrays>

    <enums>
        <use_cases>status, role, type, category with fixed values</use_cases>
        <postgresql>CREATE TYPE name AS ENUM('val1','val2')</postgresql>
        <mysql>ENUM('val1','val2','val3')</mysql>
        <mariadb>ENUM('val1','val2','val3')</mariadb>
        <sqlite>TEXT with CHECK constraint</sqlite>
        <sqlserver>VARCHAR with CHECK constraint</sqlserver>
        <oracle>VARCHAR2 with CHECK constraint</oracle>
        <mongodb>String with validation</mongodb>
        <common_enums>
            <enum name="status">draft, pending, active, completed, cancelled, archived</enum>
            <enum name="role">guest, user, moderator, admin, superadmin</enum>
            <enum name="visibility">public, private, unlisted, followers_only</enum>
            <enum name="priority">low, medium, high, urgent, critical</enum>
            <enum name="payment_status">pending, authorized, captured, refunded, failed</enum>
            <enum name="order_status">pending, confirmed, processing, shipped, delivered, cancelled</enum>
        </common_enums>
    </enums>

    <special_types>
        <type name="ip_address">
            <postgresql>INET</postgresql>
            <mysql>VARCHAR(45)</mysql>
            <mariadb>VARCHAR(45)</mariadb>
            <sqlserver>VARCHAR(45)</sqlserver>
            <oracle>VARCHAR2(45)</oracle>
        </type>
        <type name="mac_address">
            <postgresql>MACADDR</postgresql>
            <others>VARCHAR(17)</others>
        </type>
        <type name="geometric">
            <postgresql>POINT, LINE, POLYGON, etc.</postgresql>
            <mysql>GEOMETRY, POINT, POLYGON</mysql>
            <sqlserver>GEOMETRY, GEOGRAPHY</sqlserver>
            <oracle>SDO_GEOMETRY</oracle>
            <mongodb>GeoJSON</mongodb>
        </type>
        <type name="full_text">
            <postgresql>TSVECTOR</postgresql>
            <mysql>FULLTEXT index</mysql>
            <mongodb>Text index</mongodb>
        </type>
    </special_types>
</data_types>
"""
