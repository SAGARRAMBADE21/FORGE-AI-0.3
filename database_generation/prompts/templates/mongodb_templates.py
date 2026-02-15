"""MongoDB templates."""
MONGODB_TEMPLATE_XML = """
<mongodb_templates>
    <header>
        <![CDATA[
// =============================================
// FORGE Generated Schema
// Database: MongoDB
// Generated: {timestamp}
// =============================================

use {database_name};
        ]]>
    </header>

    <collection_template>
        <![CDATA[
// Collection: {collection_name}
// {collection_comment}
db.createCollection("{collection_name}", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: {required_fields},
            properties: {
                _id: { bsonType: "objectId" },
                {field_definitions}
                created_at: { bsonType: "date" },
                updated_at: { bsonType: "date" }
            }
        }
    },
    validationLevel: "moderate",
    validationAction: "error"
});
        ]]>
    </collection_template>

    <field_templates>
        <objectid>"{name}": {{ bsonType: "objectId" }}</objectid>
        <string>"{name}": {{ bsonType: "string"{min_length}{max_length}{pattern} }}</string>
        <string_enum>"{name}": {{ enum: [{enum_values}] }}</string_enum>
        <int>"{name}": {{ bsonType: "int"{minimum}{maximum} }}</int>
        <long>"{name}": {{ bsonType: "long" }}</long>
        <double>"{name}": {{ bsonType: "double" }}</double>
        <decimal>"{name}": {{ bsonType: "decimal" }}</decimal>
        <bool>"{name}": {{ bsonType: "bool" }}</bool>
        <date>"{name}": {{ bsonType: "date" }}</date>
        <object>"{name}": {{ bsonType: "object", properties: {{ {nested_properties} }} }}</object>
        <array>"{name}": {{ bsonType: "array", items: {{ {item_type} }} }}</array>
        <array_string>"{name}": {{ bsonType: "array", items: {{ bsonType: "string" }} }}</array_string>
        <array_objectid>"{name}": {{ bsonType: "array", items: {{ bsonType: "objectId" }} }}</array_objectid>
    </field_templates>

    <index_templates>
        <single>db.{collection_name}.createIndex({{ {field}: 1 }}, {{ name: "{index_name}" }});</single>
        <single_desc>db.{collection_name}.createIndex({{ {field}: -1 }}, {{ name: "{index_name}" }});</single_desc>
        <compound>db.{collection_name}.createIndex({{ {fields} }}, {{ name: "{index_name}" }});</compound>
        <unique>db.{collection_name}.createIndex({{ {field}: 1 }}, {{ name: "{index_name}", unique: true }});</unique>
        <sparse>db.{collection_name}.createIndex({{ {field}: 1 }}, {{ name: "{index_name}", sparse: true }});</sparse>
        <partial>db.{collection_name}.createIndex({{ {field}: 1 }}, {{ name: "{index_name}", partialFilterExpression: {{ {filter} }} }});</partial>
        <ttl>db.{collection_name}.createIndex({{ {field}: 1 }}, {{ name: "{index_name}", expireAfterSeconds: {seconds} }});</ttl>
        <text>db.{collection_name}.createIndex({{ {fields}: "text" }}, {{ name: "{index_name}" }});</text>
        <geospatial>db.{collection_name}.createIndex({{ {field}: "2dsphere" }}, {{ name: "{index_name}" }});</geospatial>
        <hashed>db.{collection_name}.createIndex({{ {field}: "hashed" }}, {{ name: "{index_name}" }});</hashed>
        <wildcard>db.{collection_name}.createIndex({{ "{field}.$**": 1 }}, {{ name: "{index_name}" }});</wildcard>
    </index_templates>

    <aggregation_view_template>
        <![CDATA[
// View: {view_name}
db.createView("{view_name}", "{source_collection}", [
    {pipeline_stages}
]);
        ]]>
    </aggregation_view_template>

    <sharding_template>
        <![CDATA[
// Sharding configuration for {collection_name}
sh.enableSharding("{database_name}");
sh.shardCollection("{database_name}.{collection_name}", {{ {shard_key} }});
        ]]>
    </sharding_template>

    <migration_template>
        <![CDATA[
// Migration: Add default values to existing documents
db.{collection_name}.updateMany(
    {{ {field}: {{ $exists: false }} }},
    {{ $set: {{ {field}: {default_value} }} }}
);
        ]]>
    </migration_template>

    <footer>
        <![CDATA[
// =============================================
// Schema generation complete
// =============================================
print("FORGE schema applied successfully to " + db.getName());
        ]]>
    </footer>
</mongodb_templates>
"""