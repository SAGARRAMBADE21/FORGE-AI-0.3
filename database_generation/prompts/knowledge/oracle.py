ORACLE_XML = """
<oracle>
    <info>
        <name>Oracle Database</name>
        <type>Enterprise-grade database (PL/SQL)</type>
        <features>RAC, Data Guard, partitioning, advanced compression, in-memory</features>
        <editions>Express (XE), Standard, Enterprise</editions>
    </info>

    <data_types>
        <uuid>
            <type>RAW(16) or VARCHAR2(36)</type>
            <generate>SYS_GUID()</generate>
            <example>id RAW(16) DEFAULT SYS_GUID() PRIMARY KEY</example>
        </uuid>
        <identity>
            <syntax>id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY</syntax>
            <old_style>Use SEQUENCE + TRIGGER</old_style>
        </identity>
        <strings>
            <varchar2>VARCHAR2(n BYTE) or VARCHAR2(n CHAR)</varchar2>
            <clob>CLOB - large text</clob>
            <nvarchar2>NVARCHAR2(n) - Unicode</nvarchar2>
            <max_varchar2>4000 bytes (32767 in 12c+ with MAX_STRING_SIZE=EXTENDED)</max_varchar2>
        </strings>
        <numbers>
            <number>NUMBER(p,s) - precision and scale</number>
            <integer>NUMBER(10) or INTEGER</integer>
            <float>BINARY_DOUBLE or BINARY_FLOAT</float>
        </numbers>
        <datetime>
            <date>DATE - includes time to seconds</date>
            <timestamp>TIMESTAMP - includes fractional seconds</timestamp>
            <timestamptz>TIMESTAMP WITH TIME ZONE</timestamptz>
            <interval>INTERVAL YEAR TO MONTH, INTERVAL DAY TO SECOND</interval>
        </datetime>
        <json>
            <type>JSON (21c+) or CLOB with IS JSON check</type>
            <constraint>CHECK (data IS JSON)</constraint>
        </json>
    </data_types>

    <json_support>
        <functions version="12c+">
            <func>JSON_VALUE(data, '$.key')</func>
            <func>JSON_QUERY(data, '$.object')</func>
            <func>JSON_EXISTS(data, '$.key')</func>
            <func>JSON_TABLE(data, '$.items[*]' COLUMNS (...))</func>
            <func>JSON_OBJECT(key VALUE value)</func>
            <func>JSON_ARRAY(value1, value2)</func>
            <func>JSON_ARRAYAGG(value)</func>
            <func>JSON_OBJECTAGG(key VALUE value)</func>
        </functions>
        <dot_notation version="12.2+">data.key.subkey</dot_notation>
    </json_support>

    <indexes>
        <btree>CREATE INDEX idx ON t(col)</btree>
        <bitmap>CREATE BITMAP INDEX idx ON t(col)</bitmap>
        <unique>CREATE UNIQUE INDEX idx ON t(col)</unique>
        <function_based>CREATE INDEX idx ON t(LOWER(email))</function_based>
        <json>CREATE INDEX idx ON t(data.name.value)</json>
        <text>CREATE INDEX idx ON t(content) INDEXTYPE IS CTXSYS.CONTEXT</text>
        <spatial>CREATE INDEX idx ON t(geom) INDEXTYPE IS MDSYS.SPATIAL_INDEX</spatial>
    </indexes>

    <constraints>
        <check>ALTER TABLE t ADD CONSTRAINT chk CHECK (price > 0)</check>
        <not_null>ALTER TABLE t MODIFY col NOT NULL</not_null>
        <default>ALTER TABLE t MODIFY col DEFAULT SYSDATE</default>
        <foreign_key>
            <sql>
ALTER TABLE orders ADD CONSTRAINT fk_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            </sql>
        </foreign_key>
    </constraints>

    <sequences_triggers>
        <sequence>
            <sql>
CREATE SEQUENCE user_seq START WITH 1 INCREMENT BY 1;
            </sql>
        </sequence>
        <trigger>
            <sql>
CREATE OR REPLACE TRIGGER user_bi BEFORE INSERT ON users
FOR EACH ROW BEGIN
    IF :NEW.id IS NULL THEN
        :NEW.id := user_seq.NEXTVAL;
    END IF;
    :NEW.created_at := SYSDATE;
END;
            </sql>
        </trigger>
        <updated_at>
            <sql>
CREATE OR REPLACE TRIGGER user_bu BEFORE UPDATE ON users
FOR EACH ROW BEGIN
    :NEW.updated_at := SYSDATE;
END;
            </sql>
        </updated_at>
    </sequences_triggers>

    <partitioning>
        <range>
            <sql>
CREATE TABLE orders (id NUMBER, created_at DATE, total NUMBER)
PARTITION BY RANGE (created_at) (
    PARTITION p2023 VALUES LESS THAN (DATE '2024-01-01'),
    PARTITION p2024 VALUES LESS THAN (DATE '2025-01-01'),
    PARTITION pmax VALUES LESS THAN (MAXVALUE)
);
            </sql>
        </range>
        <list>
            <sql>
CREATE TABLE users (id NUMBER, region VARCHAR2(10))
PARTITION BY LIST (region) (
    PARTITION p_us VALUES ('US-EAST', 'US-WEST'),
    PARTITION p_eu VALUES ('EU-WEST', 'EU-CENTRAL')
);
            </sql>
        </list>
        <hash>
            <sql>CREATE TABLE orders (...) PARTITION BY HASH (user_id) PARTITIONS 4;</sql>
        </hash>
    </partitioning>

    <common_operations>
        <merge>
            <sql>
MERGE INTO users t USING (SELECT 'a@b.com' email, 'A' name FROM dual) s
ON (t.email = s.email)
WHEN MATCHED THEN UPDATE SET t.name = s.name
WHEN NOT MATCHED THEN INSERT (email, name) VALUES (s.email, s.name);
            </sql>
        </merge>
        <returning>
            <sql>
INSERT INTO users (email, name) VALUES ('a@b.com', 'A')
RETURNING id INTO v_id;
            </sql>
        </returning>
        <cte>
            <sql>
WITH ActiveUsers AS (SELECT * FROM users WHERE is_active = 1)
SELECT * FROM ActiveUsers WHERE created_at > DATE '2024-01-01';
            </sql>
        </cte>
        <pagination>
            <sql>
SELECT * FROM users ORDER BY created_at
OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY;
            </sql>
        </pagination>
    </common_operations>

    <security>
        <vpd name="Virtual Private Database">
            <sql>
BEGIN
  DBMS_RLS.ADD_POLICY(
    object_schema => 'app',
    object_name => 'documents',
    policy_name => 'user_policy',
    function_schema => 'app',
    policy_function => 'user_filter_fn',
    statement_types => 'SELECT,UPDATE,DELETE'
  );
END;
            </sql>
        </vpd>
        <tde>Transparent Data Encryption</tde>
        <redaction>Data Redaction for masking</redaction>
    </security>
</oracle>
"""
