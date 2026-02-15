DATABASE_FUNDAMENTALS_XML = """
<database_fundamentals>
    <acid_properties>
        <atomicity>
            <definition>Transactions are all-or-nothing</definition>
            <behavior>All operations succeed or all fail and rollback</behavior>
        </atomicity>
        <consistency>
            <definition>Database moves from valid state to valid state</definition>
            <behavior>All integrity constraints maintained after transaction</behavior>
        </consistency>
        <isolation>
            <definition>Concurrent transactions don't interfere</definition>
            <behavior>Each transaction executes as if alone</behavior>
        </isolation>
        <durability>
            <definition>Committed data survives crashes</definition>
            <behavior>Persisted to non-volatile storage</behavior>
        </durability>
    </acid_properties>

    <isolation_levels>
        <level name="READ_UNCOMMITTED" dirty_read="yes" non_repeatable="yes" phantom="yes">
            <description>Lowest isolation, highest concurrency</description>
            <support database="postgresql">no</support>
            <support database="mysql">yes</support>
            <support database="sqlserver">yes</support>
            <support database="oracle">no</support>
            <support database="sqlite">no</support>
            <support database="mariadb">yes</support>
        </level>
        <level name="READ_COMMITTED" dirty_read="no" non_repeatable="yes" phantom="yes">
            <description>Default for most databases</description>
            <default_for>postgresql, oracle, sqlserver</default_for>
        </level>
        <level name="REPEATABLE_READ" dirty_read="no" non_repeatable="no" phantom="yes">
            <description>Default for MySQL/MariaDB InnoDB</description>
            <default_for>mysql, mariadb</default_for>
        </level>
        <level name="SERIALIZABLE" dirty_read="no" non_repeatable="no" phantom="no">
            <description>Highest isolation, lowest concurrency</description>
            <support database="all">yes</support>
        </level>
    </isolation_levels>

    <key_types>
        <primary_key>
            <definition>Uniquely identifies each row</definition>
            <nullable>no</nullable>
            <unique>yes</unique>
            <per_table>one</per_table>
            <best_practice>Use surrogate key (UUID or auto-increment)</best_practice>
        </primary_key>
        <foreign_key>
            <definition>References primary key in another table</definition>
            <enforces>referential integrity</enforces>
            <must_index>yes - critical for JOIN performance</must_index>
            <actions>CASCADE, RESTRICT, SET NULL, SET DEFAULT, NO ACTION</actions>
        </foreign_key>
        <surrogate_key>
            <definition>System-generated identifier</definition>
            <types>UUID, SERIAL, BIGSERIAL, IDENTITY, AUTO_INCREMENT</types>
            <recommendation>PREFERRED for primary keys</recommendation>
            <reason>Immutable, no business meaning to change</reason>
        </surrogate_key>
        <natural_key>
            <definition>Business-meaningful identifier</definition>
            <examples>email, SSN, ISBN, phone</examples>
            <recommendation>AVOID as primary key</recommendation>
            <reason>May change, causes cascading updates</reason>
            <use_as>UNIQUE constraint instead</use_as>
        </natural_key>
        <composite_key>
            <definition>Multiple columns form the key</definition>
            <use_cases>junction tables, compound natural identifiers</use_cases>
            <syntax>PRIMARY KEY (col1, col2)</syntax>
        </composite_key>
    </key_types>

    <constraints>
        <constraint name="NOT_NULL">
            <purpose>Prevent null values</purpose>
            <syntax>column_name TYPE NOT NULL</syntax>
        </constraint>
        <constraint name="UNIQUE">
            <purpose>All values must be distinct</purpose>
            <allows_null>yes (one null)</allows_null>
            <syntax>column_name TYPE UNIQUE</syntax>
        </constraint>
        <constraint name="PRIMARY_KEY">
            <purpose>NOT NULL + UNIQUE identifier</purpose>
            <syntax>column_name TYPE PRIMARY KEY</syntax>
        </constraint>
        <constraint name="FOREIGN_KEY">
            <purpose>Reference parent table</purpose>
            <syntax>REFERENCES table(column) ON DELETE action</syntax>
        </constraint>
        <constraint name="CHECK">
            <purpose>Custom validation expression</purpose>
            <syntax>CHECK (expression)</syntax>
            <examples>CHECK (price > 0), CHECK (status IN ('a','b'))</examples>
        </constraint>
        <constraint name="DEFAULT">
            <purpose>Value when not specified</purpose>
            <syntax>column_name TYPE DEFAULT value</syntax>
        </constraint>
    </constraints>

    <referential_actions>
        <action name="CASCADE">
            <behavior>Delete/update child rows automatically</behavior>
            <use_when>Children meaningless without parent</use_when>
        </action>
        <action name="RESTRICT">
            <behavior>Prevent if children exist (immediate check)</behavior>
            <use_when>Protect important child data</use_when>
        </action>
        <action name="NO_ACTION">
            <behavior>Prevent if children exist (deferred check)</behavior>
            <use_when>Check at transaction end</use_when>
        </action>
        <action name="SET_NULL">
            <behavior>Set FK to NULL in children</behavior>
            <use_when>Children can exist independently</use_when>
            <requires>FK column must be nullable</requires>
        </action>
        <action name="SET_DEFAULT">
            <behavior>Set FK to default value</behavior>
            <use_when>Has meaningful default parent</use_when>
        </action>
    </referential_actions>

    <sql_categories>
        <ddl name="Data Definition Language">
            <commands>CREATE, ALTER, DROP, TRUNCATE, RENAME</commands>
            <purpose>Define database structure</purpose>
        </ddl>
        <dml name="Data Manipulation Language">
            <commands>SELECT, INSERT, UPDATE, DELETE, MERGE</commands>
            <purpose>Manipulate data</purpose>
        </dml>
        <dcl name="Data Control Language">
            <commands>GRANT, REVOKE</commands>
            <purpose>Control access permissions</purpose>
        </dcl>
        <tcl name="Transaction Control Language">
            <commands>BEGIN, COMMIT, ROLLBACK, SAVEPOINT</commands>
            <purpose>Manage transactions</purpose>
        </tcl>
    </sql_categories>

    <naming_conventions>
        <rule name="case">
            <standard>snake_case for all identifiers</standard>
            <wrong>camelCase, PascalCase, UPPERCASE</wrong>
        </rule>
        <rule name="tables">
            <standard>plural nouns</standard>
            <examples>users, orders, order_items, product_categories</examples>
            <wrong>user, Order, tbl_users</wrong>
        </rule>
        <rule name="columns">
            <standard>singular descriptive names</standard>
            <examples>user_id, email, created_at, is_active</examples>
        </rule>
        <rule name="primary_key">
            <standard>id</standard>
        </rule>
        <rule name="foreign_key">
            <standard>{referenced_table_singular}_id</standard>
            <examples>user_id, order_id, category_id</examples>
        </rule>
        <rule name="timestamps">
            <standard>created_at, updated_at, deleted_at</standard>
        </rule>
        <rule name="booleans">
            <standard>is_, has_, can_ prefix</standard>
            <examples>is_active, is_verified, has_permission, can_edit</examples>
        </rule>
        <rule name="counts">
            <standard>_count suffix</standard>
            <examples>follower_count, order_count, view_count</examples>
        </rule>
        <rule name="indexes">
            <standard>idx_{table}_{columns}</standard>
            <examples>idx_users_email, idx_orders_user_id_status</examples>
        </rule>
    </naming_conventions>

    <reserved_words_avoid>
        <word>order</word><word>user</word><word>table</word><word>index</word>
        <word>key</word><word>select</word><word>from</word><word>where</word>
        <word>group</word><word>having</word><word>join</word><word>left</word>
        <word>right</word><word>inner</word><word>outer</word><word>on</word>
        <word>and</word><word>or</word><word>not</word><word>null</word>
        <word>true</word><word>false</word><word>default</word><word>primary</word>
        <word>foreign</word><word>unique</word><word>check</word><word>constraint</word>
        <word>references</word><word>cascade</word><word>database</word><word>schema</word>
    </reserved_words_avoid>
</database_fundamentals>
"""
