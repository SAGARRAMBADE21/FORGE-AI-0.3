SQLITE_TEMPLATE_XML = """
<sqlite_templates>
    <header>
        <![CDATA[
-- =============================================
-- FORGE Generated Schema
-- Database: SQLite
-- Generated: {timestamp}
-- =============================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Recommended pragmas for performance
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA busy_timeout = 5000;

BEGIN TRANSACTION;
        ]]>
    </header>

    <table_template>
        <![CDATA[
-- Table: {table_name}
-- {table_comment}
CREATE TABLE IF NOT EXISTS {table_name} (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    {columns}
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Trigger for updated_at
CREATE TRIGGER IF NOT EXISTS {table_name}_updated_at
    AFTER UPDATE ON {table_name}
    FOR EACH ROW
BEGIN
    UPDATE {table_name} SET updated_at = datetime('now') WHERE id = NEW.id;
END;
        ]]>
    </table_template>

    <column_templates>
        <uuid>{name} TEXT{not_null}{default}{unique}</uuid>
        <uuid_pk>{name} TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16))))</uuid_pk>
        <uuid_fk>{name} TEXT{not_null} REFERENCES {ref_table}({ref_column}) ON DELETE {on_delete}</uuid_fk>
        <varchar>{name} TEXT{not_null}{default}{unique}</varchar>
        <text>{name} TEXT{not_null}{default}</text>
        <integer>{name} INTEGER{not_null}{default}{check}</integer>
        <integer_pk>{name} INTEGER PRIMARY KEY AUTOINCREMENT</integer_pk>
        <real>{name} REAL{not_null}{default}</real>
        <boolean>{name} INTEGER{not_null} DEFAULT {default} CHECK ({name} IN (0, 1))</boolean>
        <datetime>{name} TEXT{not_null}{default}</datetime>
        <date>{name} TEXT{not_null}{default}</date>
        <json>{name} TEXT{not_null}{default}</json>
        <blob>{name} BLOB{not_null}</blob>
    </column_templates>

    <index_templates>
        <btree>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns});</btree>
        <unique>CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns});</unique>
        <partial>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns}) WHERE {condition};</partial>
        <expression>CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({expression});</expression>
    </index_templates>

    <constraint_templates>
        <check>-- CHECK constraint (inline): CHECK ({expression})</check>
        <foreign_key>FOREIGN KEY ({column}) REFERENCES {ref_table}({ref_column}) ON DELETE {on_delete}</foreign_key>
    </constraint_templates>

    <view_template>
        <![CDATA[
CREATE VIEW IF NOT EXISTS {view_name} AS
{select_statement};
        ]]>
    </view_template>

    <footer>
        <![CDATA[
COMMIT;

-- Analyze for query optimization
ANALYZE;

-- =============================================
-- Schema generation complete
-- =============================================
        ]]>
    </footer>
</sqlite_templates>
"""