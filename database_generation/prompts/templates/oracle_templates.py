ORACLE_TEMPLATE_XML = """
<oracle_templates>
    <header>
        <![CDATA[
-- =============================================
-- FORGE Generated Schema
-- Database: Oracle
-- Generated: {timestamp}
-- =============================================

SET DEFINE OFF;
SET SQLBLANKLINES ON;
        ]]>
    </header>

    <table_template>
        <![CDATA[
-- Table: {table_name}
-- {table_comment}
CREATE TABLE {table_name} (
    id RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    {columns}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
);

COMMENT ON TABLE {table_name} IS '{table_comment}';
        ]]>
    </table_template>

    <column_templates>
        <uuid>{name} RAW(16){not_null}{default}</uuid>
        <uuid_pk>{name} RAW(16) DEFAULT SYS_GUID() PRIMARY KEY</uuid_pk>
        <uuid_fk>{name} RAW(16){not_null} REFERENCES {ref_table}({ref_column}) ON DELETE {on_delete}</uuid_fk>
        <varchar2>{name} VARCHAR2({length}){not_null}{default}{unique}</varchar2>
        <clob>{name} CLOB{not_null}{default}</clob>
        <number>{name} NUMBER({precision},{scale}){not_null}{default}</number>
        <number_int>{name} NUMBER({precision}){not_null}{default}</number_int>
        <number_bool>{name} NUMBER(1){not_null} DEFAULT {default} CHECK ({name} IN (0, 1))</number_bool>
        <timestamp>{name} TIMESTAMP{not_null}{default}</timestamp>
        <timestamptz>{name} TIMESTAMP WITH TIME ZONE{not_null}{default}</timestamptz>
        <date>{name} DATE{not_null}{default}</date>
        <json>{name} CLOB{not_null} CONSTRAINT {table}_{name}_json CHECK ({name} IS JSON)</json>
        <blob>{name} BLOB{not_null}</blob>
        <identity>{name} NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY</identity>
    </column_templates>

    <sequence_template>
        <![CDATA[
CREATE SEQUENCE {sequence_name}
    START WITH {start}
    INCREMENT BY {increment}
    MINVALUE {min}
    MAXVALUE {max}
    {cache}
    {cycle};
        ]]>
    </sequence_template>

    <trigger_templates>
        <before_insert>
            <![CDATA[
CREATE OR REPLACE TRIGGER {table_name}_bi
BEFORE INSERT ON {table_name}
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        :NEW.id := SYS_GUID();
    END IF;
    :NEW.created_at := SYSTIMESTAMP;
    :NEW.updated_at := SYSTIMESTAMP;
END;
/
            ]]>
        </before_insert>
        <before_update>
            <![CDATA[
CREATE OR REPLACE TRIGGER {table_name}_bu
BEFORE UPDATE ON {table_name}
FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;
/
            ]]>
        </before_update>
    </trigger_templates>

    <index_templates>
        <btree>CREATE INDEX {index_name} ON {table_name}({columns});</btree>
        <unique>CREATE UNIQUE INDEX {index_name} ON {table_name}({columns});</unique>
        <bitmap>CREATE BITMAP INDEX {index_name} ON {table_name}({column});</bitmap>
        <function_based>CREATE INDEX {index_name} ON {table_name}({expression});</function_based>
        <json>CREATE INDEX {index_name} ON {table_name}({column}.{json_path});</json>
        <text>CREATE INDEX {index_name} ON {table_name}({column}) INDEXTYPE IS CTXSYS.CONTEXT;</text>
    </index_templates>

    <constraint_templates>
        <check>ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK ({expression});</check>
        <unique>ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} UNIQUE ({columns});</unique>
        <foreign_key>ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} FOREIGN KEY ({column}) REFERENCES {ref_table}({ref_column}) ON DELETE {on_delete};</foreign_key>
    </constraint_templates>

    <partitioning_templates>
        <range>
            <![CDATA[
CREATE TABLE {table_name} (
    {columns}
)
PARTITION BY RANGE ({partition_column}) (
    {partition_definitions}
);
            ]]>
        </range>
        <partition_definition>PARTITION {partition_name} VALUES LESS THAN ({value})</partition_definition>
        <list>
            <![CDATA[
CREATE TABLE {table_name} (
    {columns}
)
PARTITION BY LIST ({partition_column}) (
    {partition_definitions}
);
            ]]>
        </list>
        <list_partition>PARTITION {partition_name} VALUES ({values})</list_partition>
    </partitioning_templates>

    <vpd_template>
        <![CDATA[
-- Virtual Private Database Policy
CREATE OR REPLACE FUNCTION {function_name} (
    p_schema IN VARCHAR2,
    p_table IN VARCHAR2
) RETURN VARCHAR2 AS
BEGIN
    RETURN '{predicate}';
END;
/

BEGIN
    DBMS_RLS.ADD_POLICY(
        object_schema => '{schema}',
        object_name => '{table_name}',
        policy_name => '{policy_name}',
        function_schema => '{schema}',
        policy_function => '{function_name}',
        statement_types => '{statement_types}'
    );
END;
/
        ]]>
    </vpd_template>

    <footer>
        <![CDATA[
-- Gather statistics
BEGIN
    DBMS_STATS.GATHER_SCHEMA_STATS('{schema}');
END;
/

-- =============================================
-- Schema generation complete
-- =============================================
        ]]>
    </footer>
</oracle_templates>
"""