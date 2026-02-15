SQLSERVER_TEMPLATE_XML = """
<sqlserver_templates>
    <header>
        <![CDATA[
-- =============================================
-- FORGE Generated Schema
-- Database: SQL Server
-- Generated: {timestamp}
-- =============================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET NOCOUNT ON;

BEGIN TRANSACTION;
BEGIN TRY
        ]]>
    </header>

    <table_template>
        <![CDATA[
-- Table: {table_name}
-- {table_comment}
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{table_name}')
BEGIN
    CREATE TABLE [{schema}].[{table_name}] (
        [id] UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        {columns}
        [created_at] DATETIME2 NOT NULL DEFAULT GETDATE(),
        [updated_at] DATETIME2 NOT NULL DEFAULT GETDATE(),
        CONSTRAINT [PK_{table_name}] PRIMARY KEY CLUSTERED ([id])
    );
END;
        ]]>
    </table_template>

    <column_templates>
        <uuid>[{name}] UNIQUEIDENTIFIER{not_null}{default}{unique}</uuid>
        <uuid_pk>[{name}] UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY</uuid_pk>
        <uuid_fk>[{name}] UNIQUEIDENTIFIER{not_null}{default}</uuid_fk>
        <nvarchar>[{name}] NVARCHAR({length}){not_null}{default}{unique}</nvarchar>
        <nvarchar_max>[{name}] NVARCHAR(MAX){not_null}{default}</nvarchar_max>
        <varchar>[{name}] VARCHAR({length}){not_null}{default}{unique}</varchar>
        <int>[{name}] INT{not_null}{default}</int>
        <int_identity>[{name}] INT IDENTITY(1,1) PRIMARY KEY</int_identity>
        <bigint>[{name}] BIGINT{not_null}{default}</bigint>
        <smallint>[{name}] SMALLINT{not_null}{default}</smallint>
        <tinyint>[{name}] TINYINT{not_null}{default}</tinyint>
        <decimal>[{name}] DECIMAL({precision},{scale}){not_null}{default}</decimal>
        <money>[{name}] MONEY{not_null}{default}</money>
        <bit>[{name}] BIT{not_null} DEFAULT {default}</bit>
        <datetime2>[{name}] DATETIME2{not_null}{default}</datetime2>
        <datetimeoffset>[{name}] DATETIMEOFFSET{not_null}{default}</datetimeoffset>
        <date>[{name}] DATE{not_null}{default}</date>
        <time>[{name}] TIME{not_null}{default}</time>
        <json>[{name}] NVARCHAR(MAX){not_null} CONSTRAINT [CK_{table}_{name}_JSON] CHECK (ISJSON([{name}]) = 1)</json>
        <xml>[{name}] XML{not_null}</xml>
        <varbinary>[{name}] VARBINARY(MAX){not_null}</varbinary>
    </column_templates>

    <foreign_key_template>
        <![CDATA[
ALTER TABLE [{schema}].[{table_name}]
    ADD CONSTRAINT [FK_{table_name}_{column_name}]
    FOREIGN KEY ([{column_name}])
    REFERENCES [{schema}].[{ref_table}] ([{ref_column}])
    ON DELETE {on_delete} ON UPDATE {on_update};
        ]]>
    </foreign_key_template>

    <index_templates>
        <nonclustered>CREATE NONCLUSTERED INDEX [{index_name}] ON [{schema}].[{table_name}]({columns});</nonclustered>
        <unique>CREATE UNIQUE NONCLUSTERED INDEX [{index_name}] ON [{schema}].[{table_name}]({columns});</unique>
        <filtered>CREATE NONCLUSTERED INDEX [{index_name}] ON [{schema}].[{table_name}]({columns}) WHERE {condition};</filtered>
        <include>CREATE NONCLUSTERED INDEX [{index_name}] ON [{schema}].[{table_name}]({columns}) INCLUDE ({include_columns});</include>
        <columnstore>CREATE NONCLUSTERED COLUMNSTORE INDEX [{index_name}] ON [{schema}].[{table_name}]({columns});</columnstore>
    </index_templates>

    <constraint_templates>
        <check>ALTER TABLE [{schema}].[{table_name}] ADD CONSTRAINT [{constraint_name}] CHECK ({expression});</check>
        <default>ALTER TABLE [{schema}].[{table_name}] ADD CONSTRAINT [{constraint_name}] DEFAULT {default_value} FOR [{column}];</default>
        <unique>ALTER TABLE [{schema}].[{table_name}] ADD CONSTRAINT [{constraint_name}] UNIQUE ({columns});</unique>
    </constraint_templates>

    <trigger_templates>
        <updated_at>
            <![CDATA[
CREATE OR ALTER TRIGGER [tr_{table_name}_updated_at]
ON [{schema}].[{table_name}]
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE t SET t.[updated_at] = GETDATE()
    FROM [{schema}].[{table_name}] t
    INNER JOIN inserted i ON t.[id] = i.[id];
END;
            ]]>
        </updated_at>
    </trigger_templates>

    <partitioning_templates>
        <partition_function>
            <![CDATA[
CREATE PARTITION FUNCTION [pf_{name}] ({data_type})
AS RANGE {range_type} FOR VALUES ({boundary_values});
            ]]>
        </partition_function>
        <partition_scheme>
            <![CDATA[
CREATE PARTITION SCHEME [ps_{name}]
AS PARTITION [pf_{name}]
TO ({filegroups});
            ]]>
        </partition_scheme>
    </partitioning_templates>

    <footer>
        <![CDATA[
    COMMIT TRANSACTION;
    PRINT 'Schema generation complete';
END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    PRINT 'Error: ' + ERROR_MESSAGE();
    THROW;
END CATCH;

-- =============================================
-- Schema generation complete
-- =============================================
        ]]>
    </footer>
</sqlserver_templates>
"""