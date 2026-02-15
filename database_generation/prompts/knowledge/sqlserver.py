SQLSERVER_XML = """
<sqlserver>
    <info>
        <name>SQL Server</name>
        <type>Microsoft enterprise database (T-SQL)</type>
        <features>Advanced analytics, Always On, columnstore, in-memory OLTP</features>
        <editions>Express (free), Standard, Enterprise, Azure SQL</editions>
    </info>

    <data_types>
        <uuid>
            <type>UNIQUEIDENTIFIER</type>
            <generate>NEWID()</generate>
            <sequential>NEWSEQUENTIALID()</sequential>
            <example>id UNIQUEIDENTIFIER DEFAULT NEWID() PRIMARY KEY</example>
        </uuid>
        <identity>
            <syntax>INT IDENTITY(1,1) PRIMARY KEY</syntax>
            <get_value>SCOPE_IDENTITY()</get_value>
        </identity>
        <strings>
            <varchar>VARCHAR(n) - ASCII, max 8000</varchar>
            <nvarchar>NVARCHAR(n) - Unicode, max 4000</nvarchar>
            <max>NVARCHAR(MAX) - up to 2GB</max>
        </strings>
        <datetime>
            <date>DATE</date>
            <time>TIME</time>
            <datetime2>DATETIME2 (preferred over DATETIME)</datetime2>
            <datetimeoffset>DATETIMEOFFSET (with timezone)</datetimeoffset>
        </datetime>
        <json>
            <storage>NVARCHAR(MAX)</storage>
            <validate>ISJSON(column) = 1</validate>
        </json>
    </data_types>

    <json_support>
        <functions>
            <func>JSON_VALUE(json, '$.key')</func>
            <func>JSON_QUERY(json, '$.object')</func>
            <func>JSON_MODIFY(json, '$.key', value)</func>
            <func>ISJSON(string)</func>
            <func>OPENJSON(json)</func>
            <func>FOR JSON PATH</func>
            <func>FOR JSON AUTO</func>
        </functions>
        <example>
SELECT JSON_VALUE(data, '$.name') AS name FROM users WHERE ISJSON(data) = 1;
SELECT * FROM OPENJSON(@json) WITH (name NVARCHAR(100), age INT);
SELECT * FROM users FOR JSON PATH;
        </example>
    </json_support>

    <indexes>
        <clustered>CREATE CLUSTERED INDEX idx ON t(col)</clustered>
        <nonclustered>CREATE NONCLUSTERED INDEX idx ON t(col)</nonclustered>
        <unique>CREATE UNIQUE INDEX idx ON t(col)</unique>
        <filtered>CREATE INDEX idx ON t(col) WHERE status = 'active'</filtered>
        <include>CREATE INDEX idx ON t(col) INCLUDE (col2, col3)</include>
        <columnstore>CREATE COLUMNSTORE INDEX idx ON t(col1, col2)</columnstore>
        <fulltext>CREATE FULLTEXT INDEX ON t(col) KEY INDEX pk_idx</fulltext>
    </indexes>

    <constraints>
        <check>ALTER TABLE t ADD CONSTRAINT chk CHECK (price > 0)</check>
        <default>ALTER TABLE t ADD CONSTRAINT df DEFAULT GETDATE() FOR created_at</default>
        <foreign_key>
            <sql>
ALTER TABLE orders ADD CONSTRAINT fk_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            </sql>
        </foreign_key>
    </constraints>

    <triggers>
        <updated_at>
            <sql>
CREATE TRIGGER tr_updated ON users AFTER UPDATE AS
BEGIN
    UPDATE users SET updated_at = GETDATE()
    FROM users u INNER JOIN inserted i ON u.id = i.id;
END;
            </sql>
        </updated_at>
    </triggers>

    <partitioning>
        <function>
            <sql>
CREATE PARTITION FUNCTION pf_date (DATE)
AS RANGE RIGHT FOR VALUES ('2023-01-01', '2024-01-01', '2025-01-01');
            </sql>
        </function>
        <scheme>
            <sql>
CREATE PARTITION SCHEME ps_date AS PARTITION pf_date TO ([PRIMARY], [PRIMARY], [PRIMARY], [PRIMARY]);
            </sql>
        </scheme>
        <table>
            <sql>
CREATE TABLE orders (id INT, created_at DATE, total DECIMAL(10,2))
ON ps_date(created_at);
            </sql>
        </table>
    </partitioning>

    <common_operations>
        <merge>
            <sql>
MERGE INTO users AS target
USING (SELECT 'a@b.com' AS email, 'A' AS name) AS source
ON target.email = source.email
WHEN MATCHED THEN UPDATE SET name = source.name
WHEN NOT MATCHED THEN INSERT (email, name) VALUES (source.email, source.name);
            </sql>
        </merge>
        <output>
            <insert>INSERT INTO users (email) OUTPUT inserted.id VALUES ('a@b.com')</insert>
            <update>UPDATE users SET name = 'B' OUTPUT inserted.* WHERE id = 1</update>
            <delete>DELETE FROM users OUTPUT deleted.* WHERE id = 1</delete>
        </output>
        <cte>
            <sql>
WITH ActiveUsers AS (SELECT * FROM users WHERE is_active = 1)
SELECT * FROM ActiveUsers WHERE created_at > '2024-01-01';
            </sql>
        </cte>
    </common_operations>

    <security>
        <row_level_security>
            <sql>
CREATE FUNCTION dbo.fn_userfilter(@user_id INT) RETURNS TABLE
WITH SCHEMABINDING AS RETURN SELECT 1 AS result WHERE @user_id = USER_ID();

CREATE SECURITY POLICY UserFilter ADD FILTER PREDICATE dbo.fn_userfilter(user_id) ON dbo.documents;
            </sql>
        </row_level_security>
        <always_encrypted>Column-level encryption for sensitive data</always_encrypted>
        <tde>Transparent Data Encryption for database files</tde>
    </security>
</sqlserver>
"""
