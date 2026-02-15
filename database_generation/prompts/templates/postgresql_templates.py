"""PostgreSQL templates."""
POSTGRESQL_TEMPLATE_XML = """
<postgresql_templates>
    <header>
        <![CDATA[
-- =============================================
-- FORGE Generated Schema
-- Database: PostgreSQL
-- Generated: {timestamp}
-- =============================================

BEGIN;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        ]]>
    </header>

    <function name="update_updated_at">
        <![CDATA[
-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
        ]]>
    </function>

    <enum_template>
        <![CDATA[
-- Enum: {enum_name}
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
        CREATE TYPE {enum_name} AS ENUM ({enum_values});
    END IF;
END $$;
        ]]>
    </enum_template>

    <table_template>
        <![CDATA[
-- Table: {table_name}
-- {table_comment}
CREATE TABLE IF NOT EXISTS {table_name} (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    {columns}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS {table_name}_updated_at ON {table_name};
CREATE TRIGGER {table_name}_updated_at
    BEFORE UPDATE ON {table_name}
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
        ]]>
    </table_template>

    <column_templates>
        <uuid>{name} UUID{not_null}{default}{unique}</uuid>
        <uuid_pk>{name} UUID DEFAULT gen_random_uuid() PRIMARY KEY</uuid_pk>
        <uuid_fk>{name} UUID{not_null} REFERENCES {ref_table}({ref_column}) ON DELETE {on_delete}</uuid_fk>
        <varchar>{name} VARCHAR({length}){not_null}{default}{unique}</varchar>
        <text>{name} TEXT{not_null}{default}</text>
        <integer>{name} INTEGER{not_null}{default}{check}</integer>
        <bigint>{name} BIGINT{not_null}{default}</bigint>
        <smallint>{name} SMALLINT{not_null}{default}{check}</smallint>
        <decimal>{name} NUMERIC({precision},{scale}){not_null}{default}{check}</decimal>
        <boolean>{name} BOOLEAN{not_null} DEFAULT {default}</boolean>
        <timestamptz>{name} TIMESTAMPTZ{not_null}{default}</timestamptz>
        <date>{name} DATE{not_null}{default}</date>
        <time>{name} TIME{not_null}{default}</time>
        <jsonb>{name} JSONB{not_null} DEFAULT '{default}'::jsonb</jsonb>
        <text_array>{name} TEXT[]{not_null} DEFAULT '{}'</text_array>
        <uuid_array>{name} UUID[]{not_null} DEFAULT '{}'</uuid_array>
        <enum>{name} {enum_type}{not_null}{default}</enum>
        <inet>{name} INET{not_null}</inet>
    </column_templates>

    <index_templates>
        <btree>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns});</btree>
        <btree_desc>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns} DESC);</btree_desc>
        <unique>CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns});</unique>
        <partial>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns}) WHERE {condition};</partial>
        <partial_unique>CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns}) WHERE {condition};</partial_unique>
        <gin>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING GIN({column});</gin>
        <gin_jsonb_path>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING GIN({column} jsonb_path_ops);</gin_jsonb_path>
        <gist>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING GIST({column});</gist>
        <brin>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING BRIN({column});</brin>
        <expression>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}(({expression}));</expression>
        <covering>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns}) INCLUDE ({include_columns});</covering>
    </index_templates>

    <constraint_templates>
        <check>ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK ({expression});</check>
        <unique>ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} UNIQUE ({columns});</unique>
        <foreign_key>ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} FOREIGN KEY ({column}) REFERENCES {ref_table}({ref_column}) ON DELETE {on_delete};</foreign_key>
        <exclusion>ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} EXCLUDE USING GIST ({exclusion_elements});</exclusion>
    </constraint_templates>

    <trigger_templates>
        <audit>
            <![CDATA[
CREATE OR REPLACE FUNCTION audit_{table_name}()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, action, new_values, changed_by, changed_at)
        VALUES ('{table_name}', NEW.id, 'INSERT', row_to_json(NEW), current_setting('app.user_id', true)::UUID, NOW());
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by, changed_at)
        VALUES ('{table_name}', NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW), current_setting('app.user_id', true)::UUID, NOW());
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, changed_by, changed_at)
        VALUES ('{table_name}', OLD.id, 'DELETE', row_to_json(OLD), current_setting('app.user_id', true)::UUID, NOW());
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER {table_name}_audit
    AFTER INSERT OR UPDATE OR DELETE ON {table_name}
    FOR EACH ROW
    EXECUTE FUNCTION audit_{table_name}();
            ]]>
        </audit>
    </trigger_templates>

    <partitioning_templates>
        <range>
            <![CDATA[
CREATE TABLE {table_name} (
    {columns}
) PARTITION BY RANGE ({partition_column});

CREATE TABLE {table_name}_{partition_name} PARTITION OF {table_name}
    FOR VALUES FROM ('{from_value}') TO ('{to_value}');
            ]]>
        </range>
        <list>
            <![CDATA[
CREATE TABLE {table_name} (
    {columns}
) PARTITION BY LIST ({partition_column});

CREATE TABLE {table_name}_{partition_name} PARTITION OF {table_name}
    FOR VALUES IN ({values});
            ]]>
        </list>
        <hash>
            <![CDATA[
CREATE TABLE {table_name} (
    {columns}
) PARTITION BY HASH ({partition_column});

CREATE TABLE {table_name}_{partition_num} PARTITION OF {table_name}
    FOR VALUES WITH (MODULUS {modulus}, REMAINDER {remainder});
            ]]>
        </hash>
    </partitioning_templates>

    <rls_templates>
        <enable>ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;</enable>
        <policy>CREATE POLICY {policy_name} ON {table_name} FOR {operation} USING ({expression});</policy>
        <policy_with_check>CREATE POLICY {policy_name} ON {table_name} FOR {operation} USING ({using_expression}) WITH CHECK ({check_expression});</policy_with_check>
    </rls_templates>

    <footer>
        <![CDATA[
COMMIT;

-- =============================================
-- Schema generation complete
-- =============================================
        ]]>
    </footer>
</postgresql_templates>
"""