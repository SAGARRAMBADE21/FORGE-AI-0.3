"""Database security knowledge base."""
SECURITY_XML = """
<security>
    <authentication_authorization>
        <principle name="least_privilege">
            <description>Grant minimum permissions needed</description>
            <sql>
-- Create application role
CREATE ROLE app_user LOGIN PASSWORD 'secure_password';

-- Grant only necessary permissions
GRANT SELECT, INSERT, UPDATE ON users TO app_user;
GRANT SELECT ON products TO app_user;
-- No DELETE unless needed
-- No DDL (CREATE, ALTER, DROP)
            </sql>
        </principle>

        <separate_roles>
            <role name="readonly">
                <sql>
CREATE ROLE readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
                </sql>
            </role>
            <role name="readwrite">
                <sql>
CREATE ROLE readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO readwrite;
                </sql>
            </role>
            <role name="admin">
                <sql>
CREATE ROLE admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
                </sql>
            </role>
        </separate_roles>
    </authentication_authorization>

    <sql_injection>
        <never_do_this>
            <description>String concatenation with user input</description>
            <python>
# DANGEROUS - SQL Injection vulnerable
query = f"SELECT * FROM users WHERE email = '{user_input}'"
# Attack: ' OR '1'='1' --
            </python>
        </never_do_this>

        <always_do_this>
            <description>Parameterized queries</description>
            <python>
# SAFE - Parameterized
cursor.execute("SELECT * FROM users WHERE email = %s", (user_input,))

# SAFE - ORM
User.query.filter_by(email=user_input).first()
            </python>
            <all_languages>
                <postgresql format="$n">SELECT * FROM users WHERE email = $1</postgresql>
                <mysql format="?">SELECT * FROM users WHERE email = ?</mysql>
                <sqlserver format="@param">SELECT * FROM users WHERE email = @email</sqlserver>
                <oracle format=":name">SELECT * FROM users WHERE email = :email</oracle>
            </all_languages>
        </always_do_this>
    </sql_injection>

    <password_storage>
        <never>Store plain text passwords</never>
        <algorithms>
            <algorithm name="bcrypt" recommended="yes">
                <cost_factor>12+</cost_factor>
                <output_length>60 characters</output_length>
            </algorithm>
            <algorithm name="argon2" recommended="yes">
                <memory>64MB</memory>
                <iterations>3</iterations>
                <output_length>97+ characters</output_length>
            </algorithm>
            <algorithm name="pbkdf2">
                <iterations>100000+</iterations>
                <requires>salt</requires>
            </algorithm>
        </algorithms>
        <never_use>MD5, SHA1, SHA256 without salt and iterations</never_use>
        <schema>
            <sql>
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL  -- bcrypt/argon2 hash
);
            </sql>
        </schema>
    </password_storage>

    <sensitive_data>
        <pii name="Personally Identifiable Information">
            <fields>name, email, phone, address, date_of_birth, SSN, passport</fields>
            <fields>IP address, device ID, location</fields>
        </pii>
        <financial>
            <fields>credit card, bank account, transaction details</fields>
        </financial>
        <health>
            <fields>medical records, health conditions</fields>
        </health>
    </sensitive_data>

    <encryption_at_rest>
        <postgresql>
            <extension>pgcrypto</extension>
            <encrypt>INSERT INTO secrets (data) VALUES (pgp_sym_encrypt('secret', 'key'))</encrypt>
            <decrypt>SELECT pgp_sym_decrypt(data, 'key') FROM secrets</decrypt>
        </postgresql>
        <mysql>
            <encrypt>INSERT INTO secrets (data) VALUES (AES_ENCRYPT('secret', 'key'))</encrypt>
            <decrypt>SELECT AES_DECRYPT(data, 'key') FROM secrets</decrypt>
        </mysql>
        <sqlserver>
            <feature>Always Encrypted, Transparent Data Encryption (TDE)</feature>
        </sqlserver>
        <oracle>
            <feature>Transparent Data Encryption (TDE)</feature>
        </oracle>
    </encryption_at_rest>

    <data_masking>
        <sql>
CREATE VIEW users_masked AS
SELECT 
    id,
    CONCAT(LEFT(email, 2), '***@***', RIGHT(email, 4)) as email,
    CONCAT(LEFT(name, 1), '***') as name,
    CONCAT('***-***-', RIGHT(phone, 4)) as phone
FROM users;
        </sql>
    </data_masking>

    <row_level_security database="postgresql">
        <enable>ALTER TABLE documents ENABLE ROW LEVEL SECURITY</enable>
        <policies>
            <policy name="user_isolation">
                <sql>
CREATE POLICY user_docs ON documents
    FOR ALL USING (user_id = current_setting('app.user_id')::UUID);
                </sql>
            </policy>
            <policy name="org_isolation">
                <sql>
CREATE POLICY org_docs ON documents
    FOR SELECT USING (org_id = current_setting('app.org_id')::UUID);
                </sql>
            </policy>
            <policy name="admin_bypass">
                <sql>
CREATE POLICY admin_all ON documents
    FOR ALL TO admin_role USING (true);
                </sql>
            </policy>
        </policies>
        <usage>
            <sql>SET app.user_id = 'uuid-here';</sql>
        </usage>
    </row_level_security>

    <audit_logging>
        <schema>
            <sql>
CREATE TABLE audit_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(10) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by UUID,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_changed_at ON audit_log(changed_at);
            </sql>
        </schema>
        <trigger>
            <postgresql>
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, action, new_values, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW), 
                current_setting('app.user_id', true)::UUID);
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW),
                current_setting('app.user_id', true)::UUID);
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD),
                current_setting('app.user_id', true)::UUID);
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
            </postgresql>
        </trigger>
    </audit_logging>

    <connection_security>
        <postgresql>
            <config file="pg_hba.conf">hostssl all all 0.0.0.0/0 scram-sha-256</config>
        </postgresql>
        <mysql>
            <sql>ALTER USER 'app'@'%' REQUIRE SSL;</sql>
        </mysql>
        <sqlserver>
            <setting>Force Protocol Encryption = Yes</setting>
        </sqlserver>
    </connection_security>

    <checklist>
        <item checked="required">No plain text passwords</item>
        <item checked="required">Parameterized queries everywhere</item>
        <item checked="required">Encrypted connections (SSL/TLS)</item>
        <item checked="required">Limited database user permissions</item>
        <item checked="required">No public database access</item>
        <item checked="required">Firewall rules configured</item>
        <item checked="required">Secrets in environment variables</item>
        <item checked="recommended">Row-level security</item>
        <item checked="recommended">Audit logging</item>
        <item checked="recommended">Encrypted backups</item>
        <item checked="recommended">Regular password rotation</item>
        <item checked="recommended">Failed login monitoring</item>
        <item checked="recommended">Data masking for non-prod</item>
    </checklist>
</security>
"""
