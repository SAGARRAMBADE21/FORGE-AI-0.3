"""MySQL templates."""
MYSQL_TEMPLATE_XML = """
<mysql_templates>
    <header>
        <![CDATA[
-- =============================================
-- FORGE Generated Schema
-- Database: MySQL
-- Generated: {timestamp}
-- =============================================

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

START TRANSACTION;
        ]]>
    </header>

    <table_template>
        <![CDATA[
-- Table: {table_name}
-- {table_comment}
CREATE TABLE IF NOT EXISTS `{table_name}` (
    `id` CHAR(36) NOT NULL DEFAULT (UUID()),
    {columns}
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ]]>
    </table_template>

    <column_templates>
        <uuid>`{name}` CHAR(36){not_null}{default}{unique}</uuid>
        <uuid_pk>`{name}` CHAR(36) NOT NULL DEFAULT (UUID()) PRIMARY KEY</uuid_pk>
        <uuid_fk>`{name}` CHAR(36){not_null}{default}</uuid_fk>
        <varchar>`{name}` VARCHAR({length}){not_null}{default}{unique}</varchar>
        <text>`{name}` TEXT{not_null}</text>
        <longtext>`{name}` LONGTEXT{not_null}</longtext>
        <integer>`{name}` INT{not_null}{default}</integer>
        <integer_auto>`{name}` INT NOT NULL AUTO_INCREMENT PRIMARY KEY</integer_auto>
        <bigint>`{name}` BIGINT{not_null}{default}</bigint>
        <smallint>`{name}` SMALLINT{not_null}{default}</smallint>
        <tinyint>`{name}` TINYINT{not_null}{default}</tinyint>
        <decimal>`{name}` DECIMAL({precision},{scale}){not_null}{default}</decimal>
        <boolean>`{name}` TINYINT(1){not_null} DEFAULT {default}</boolean>
        <timestamp>`{name}` TIMESTAMP{not_null}{default}</timestamp>
        <datetime>`{name}` DATETIME{not_null}{default}</datetime>
        <date>`{name}` DATE{not_null}{default}</date>
        <time>`{name}` TIME{not_null}{default}</time>
        <json>`{name}` JSON{not_null}</json>
        <enum>`{name}` ENUM({enum_values}){not_null}{default}</enum>
        <blob>`{name}` BLOB{not_null}</blob>
    </column_templates>

    <foreign_key_template>
        <![CDATA[
ALTER TABLE `{table_name}` ADD CONSTRAINT `fk_{table_name}_{column_name}`
    FOREIGN KEY (`{column_name}`) REFERENCES `{ref_table}` (`{ref_column}`)
    ON DELETE {on_delete} ON UPDATE {on_update};
        ]]>
    </foreign_key_template>

    <index_templates>
        <btree>CREATE INDEX `{index_name}` ON `{table_name}` ({columns});</btree>
        <unique>CREATE UNIQUE INDEX `{index_name}` ON `{table_name}` ({columns});</unique>
        <fulltext>CREATE FULLTEXT INDEX `{index_name}` ON `{table_name}` ({columns});</fulltext>
        <spatial>CREATE SPATIAL INDEX `{index_name}` ON `{table_name}` (`{column}`);</spatial>
        <functional>CREATE INDEX `{index_name}` ON `{table_name}` (({expression}));</functional>
    </index_templates>

    <constraint_templates>
        <check>ALTER TABLE `{table_name}` ADD CONSTRAINT `{constraint_name}` CHECK ({expression});</check>
        <unique>ALTER TABLE `{table_name}` ADD CONSTRAINT `{constraint_name}` UNIQUE ({columns});</unique>
    </constraint_templates>

    <trigger_templates>
        <before_insert>
            <![CDATA[
DELIMITER //
CREATE TRIGGER `{table_name}_before_insert`
BEFORE INSERT ON `{table_name}`
FOR EACH ROW
BEGIN
    IF NEW.`id` IS NULL OR NEW.`id` = '' THEN
        SET NEW.`id` = UUID();
    END IF;
END//
DELIMITER ;
            ]]>
        </before_insert>
        <after_update>
            <![CDATA[
DELIMITER //
CREATE TRIGGER `{table_name}_after_update`
AFTER UPDATE ON `{table_name}`
FOR EACH ROW
BEGIN
    INSERT INTO `audit_log` (`table_name`, `record_id`, `action`, `old_values`, `new_values`, `changed_at`)
    VALUES ('{table_name}', NEW.`id`, 'UPDATE', JSON_OBJECT({old_columns}), JSON_OBJECT({new_columns}), NOW());
END//
DELIMITER ;
            ]]>
        </after_update>
    </trigger_templates>

    <partitioning_templates>
        <range>
            <![CDATA[
CREATE TABLE `{table_name}` (
    {columns},
    PRIMARY KEY (`id`, `{partition_column}`)
) ENGINE=InnoDB
PARTITION BY RANGE ({partition_expression}) (
    {partition_definitions}
);
            ]]>
        </range>
        <partition_definition>PARTITION `{partition_name}` VALUES LESS THAN ({value})</partition_definition>
    </partitioning_templates>

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
</mysql_templates>
"""