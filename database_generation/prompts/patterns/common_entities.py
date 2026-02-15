"""Common entity patterns."""
COMMON_ENTITIES_XML = """
<common_entities>
    <entity_template name="user_base">
        <field name="id" type="uuid" primary_key="true" default="gen_random_uuid()"/>
        <field name="email" type="varchar(255)" unique="true" required="true"/>
        <field name="password_hash" type="varchar(255)" required="true"/>
        <field name="name" type="varchar(100)"/>
        <field name="avatar_url" type="varchar(500)"/>
        <field name="is_active" type="boolean" default="true"/>
        <field name="is_verified" type="boolean" default="false"/>
        <field name="last_login_at" type="timestamptz"/>
        <field name="created_at" type="timestamptz" default="NOW()"/>
        <field name="updated_at" type="timestamptz" default="NOW()"/>
    </entity_template>

    <entity_template name="timestamps">
        <field name="created_at" type="timestamptz" default="NOW()" required="true"/>
        <field name="updated_at" type="timestamptz" default="NOW()" required="true"/>
        <trigger name="update_timestamp">
            <postgresql>
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER {table}_updated BEFORE UPDATE ON {table}
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
            </postgresql>
        </trigger>
    </entity_template>

    <entity_template name="soft_delete">
        <field name="deleted_at" type="timestamptz"/>
        <index fields="id" partial="deleted_at IS NULL"/>
        <query_pattern>WHERE deleted_at IS NULL</query_pattern>
    </entity_template>

    <entity_template name="audit_fields">
        <field name="created_by" type="uuid" references="users(id)"/>
        <field name="updated_by" type="uuid" references="users(id)"/>
        <field name="created_at" type="timestamptz" default="NOW()"/>
        <field name="updated_at" type="timestamptz" default="NOW()"/>
    </entity_template>

    <entity_template name="slug_pattern">
        <field name="name" type="varchar(100)" required="true"/>
        <field name="slug" type="varchar(100)" unique="true" required="true"/>
        <generation>lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g'))</generation>
    </entity_template>

    <entity_template name="address">
        <field name="id" type="uuid" primary_key="true"/>
        <field name="addressable_type" type="varchar(50)"/>
        <field name="addressable_id" type="uuid"/>
        <field name="type" type="enum" values="shipping,billing,home,work"/>
        <field name="is_default" type="boolean" default="false"/>
        <field name="first_name" type="varchar(50)"/>
        <field name="last_name" type="varchar(50)"/>
        <field name="company" type="varchar(100)"/>
        <field name="address_line_1" type="varchar(255)" required="true"/>
        <field name="address_line_2" type="varchar(255)"/>
        <field name="city" type="varchar(100)" required="true"/>
        <field name="state" type="varchar(100)"/>
        <field name="postal_code" type="varchar(20)" required="true"/>
        <field name="country_code" type="char(2)" required="true"/>
        <field name="phone" type="varchar(20)"/>
        <field name="created_at" type="timestamptz" default="NOW()"/>
        <field name="updated_at" type="timestamptz" default="NOW()"/>
    </entity_template>

    <entity_template name="settings_pattern">
        <field name="settings" type="jsonb" default="'{}'"/>
        <field name="preferences" type="jsonb" default="'{}'"/>
        <field name="metadata" type="jsonb" default="'{}'"/>
    </entity_template>

    <entity_template name="file_media">
        <field name="id" type="uuid" primary_key="true"/>
        <field name="user_id" type="uuid" references="users(id)"/>
        <field name="filename" type="varchar(255)" required="true"/>
        <field name="original_filename" type="varchar(255)"/>
        <field name="mime_type" type="varchar(100)"/>
        <field name="file_size" type="bigint"/>
        <field name="storage_path" type="varchar(500)" required="true"/>
        <field name="url" type="varchar(500)"/>
        <field name="thumbnail_url" type="varchar(500)"/>
        <field name="metadata" type="jsonb"/>
        <field name="created_at" type="timestamptz" default="NOW()"/>
    </entity_template>

    <entity_template name="notification">
        <field name="id" type="uuid" primary_key="true"/>
        <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
        <field name="type" type="varchar(50)" required="true"/>
        <field name="title" type="varchar(255)"/>
        <field name="content" type="text"/>
        <field name="data" type="jsonb"/>
        <field name="is_read" type="boolean" default="false"/>
        <field name="read_at" type="timestamptz"/>
        <field name="created_at" type="timestamptz" default="NOW()"/>
        <index fields="user_id,created_at" order="DESC"/>
        <index fields="user_id,is_read" partial="is_read = FALSE"/>
    </entity_template>

    <entity_template name="activity_log">
        <field name="id" type="uuid" primary_key="true"/>
        <field name="user_id" type="uuid" references="users(id)"/>
        <field name="action" type="varchar(100)" required="true"/>
        <field name="subject_type" type="varchar(50)"/>
        <field name="subject_id" type="uuid"/>
        <field name="properties" type="jsonb"/>
        <field name="ip_address" type="inet"/>
        <field name="user_agent" type="text"/>
        <field name="created_at" type="timestamptz" default="NOW()"/>
        <index fields="user_id,created_at" order="DESC"/>
        <index fields="subject_type,subject_id"/>
    </entity_template>

    <entity_template name="tagging">
        <tags_table>
            <field name="id" type="uuid" primary_key="true"/>
            <field name="name" type="varchar(50)" required="true"/>
            <field name="slug" type="varchar(50)" unique="true" required="true"/>
        </tags_table>
        <junction_table name="{entity}_tags">
            <field name="{entity}_id" type="uuid" references="{entity}(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="tag_id" type="uuid" references="tags(id)" on_delete="CASCADE" primary_key="true"/>
        </junction_table>
    </entity_template>

    <entity_template name="hierarchical">
        <field name="id" type="uuid" primary_key="true"/>
        <field name="parent_id" type="uuid" references="{self}(id)" on_delete="CASCADE"/>
        <field name="name" type="varchar(100)" required="true"/>
        <field name="slug" type="varchar(100)" unique="true" required="true"/>
        <field name="depth" type="integer" default="0"/>
        <field name="path" type="text"/>
        <field name="sort_order" type="integer" default="0"/>
        <index fields="parent_id"/>
        <index fields="path"/>
    </entity_template>

    <entity_template name="polymorphic_comments">
        <field name="id" type="uuid" primary_key="true"/>
        <field name="commentable_type" type="varchar(50)" required="true"/>
        <field name="commentable_id" type="uuid" required="true"/>
        <field name="user_id" type="uuid" references="users(id)"/>
        <field name="parent_id" type="uuid" references="comments(id)"/>
        <field name="content" type="text" required="true"/>
        <field name="status" type="enum" values="pending,approved,spam" default="pending"/>
        <field name="created_at" type="timestamptz" default="NOW()"/>
        <index fields="commentable_type,commentable_id"/>
    </entity_template>
</common_entities>
"""