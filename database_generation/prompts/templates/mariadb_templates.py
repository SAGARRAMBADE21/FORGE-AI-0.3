MARIADB_TEMPLATE_XML = """
<mariadb_templates>
    <header>
        <![CDATA[
-- =============================================
-- FORGE Generated Schema
-- Database: MariaDB
-- Generated: {timestamp}
-- =============================================

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL';

START TRANSACTION;
        ]]>
    </header>

    <table_template>
        <![CDATA[
-- Table: {table_name}
-- {table_comment}
CREATE TABLE IF NOT EXISTS `{table_name}` (
    `id` UUID NOT NULL DEFAULT UUID(),
    {columns}
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ]]>
    </table_template>

    <column_templates>
        <uuid>`{name}` UUID{not_null}{default}{unique}</uuid>
        <uuid_pk>`{name}` UUID NOT NULL DEFAULT UUID() PRIMARY KEY</uuid_pk>
        <varchar>`{name}` VARCHAR({length}){not_null}{default}{unique}</varchar>
        <text>`{name}` TEXT{not_null}</text>
        <integer>`{name}` INT{not_null}{default}</integer>
        <bigint>`{name}` BIGINT{not_null}{default}</bigint>
        <decimal>`{name}` DECIMAL({precision},{scale}){not_null}{default}</decimal>
        <boolean>`{name}` TINYINT(1){not_null} DEFAULT {default}</boolean>
        <timestamp>`{name}` TIMESTAMP{not_null}{default}</timestamp>
        <datetime>`{name}` DATETIME{not_null}{default}</datetime>
        <json>`{name}` JSON{not_null}</json>
        <enum>`{name}` ENUM({enum_values}){not_null}{default}</enum>
    </column_templates>

    <sequence_template>
        <![CDATA[
CREATE SEQUENCE IF NOT EXISTS `{sequence_name}`
    START WITH {start}
    INCREMENT BY {increment}
    MINVALUE {min}
    MAXVALUE {max}
    {cycle};
        ]]>
    </sequence_template>

    <temporal_table_template>
        <![CDATA[
-- Temporal Table: {table_name}
CREATE TABLE IF NOT EXISTS `{table_name}` (
    `id` UUID NOT NULL DEFAULT UUID(),
    {columns}
    `valid_from` TIMESTAMP(6) GENERATED ALWAYS AS ROW START,
    `valid_to` TIMESTAMP(6) GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME (`valid_from`, `valid_to`),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB WITH SYSTEM VERSIONING;
        ]]>
    </temporal_table_template>

    <index_templates>
        <btree>CREATE INDEX `{index_name}` ON `{table_name}` ({columns});</btree>
        <unique>CREATE UNIQUE INDEX `{index_name}` ON `{table_name}` ({columns});</unique>
        <fulltext>CREATE FULLTEXT INDEX `{index_name}` ON `{table_name}` ({columns});</fulltext>
        <hash>CREATE INDEX `{index_name}` USING HASH ON `{table_name}` ({columns});</hash>
    </index_templates>

    <footer>
        <![CDATA[
COMMIT;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;

-- =============================================
-- Schema generation complete
-- =============================================
        ]]>
    </footer>
</mariadb_templates>
"""