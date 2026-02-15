"""SaaS application database patterns."""
SAAS_XML = """
<saas_pattern>
    <signals>
        <signal>organizations</signal><signal>tenants</signal><signal>workspaces</signal>
        <signal>teams</signal><signal>members</signal><signal>roles</signal>
        <signal>subscriptions</signal><signal>plans</signal><signal>billing</signal>
        <signal>permissions</signal><signal>invitations</signal><signal>api_keys</signal>
    </signals>

    <entities>
        <entity name="organizations">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="name" type="varchar(100)" required="true"/>
            <field name="slug" type="varchar(100)" unique="true" required="true"/>
            <field name="logo_url" type="varchar(500)"/>
            <field name="domain" type="varchar(255)" unique="true"/>
            <field name="settings" type="jsonb" default="'{}'"/>
            <field name="metadata" type="jsonb" default="'{}'"/>
            <field name="owner_id" type="uuid" references="users(id)"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="trial_ends_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="slug"/>
        </entity>

        <entity name="users">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="email" type="varchar(255)" unique="true" required="true"/>
            <field name="password_hash" type="varchar(255)"/>
            <field name="name" type="varchar(100)"/>
            <field name="avatar_url" type="varchar(500)"/>
            <field name="phone" type="varchar(20)"/>
            <field name="timezone" type="varchar(50)" default="UTC"/>
            <field name="locale" type="varchar(10)" default="en"/>
            <field name="is_verified" type="boolean" default="false"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="last_login_at" type="timestamptz"/>
            <field name="last_login_ip" type="inet"/>
            <field name="settings" type="jsonb" default="'{}'"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="organization_members">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)" on_delete="CASCADE" required="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="role_id" type="uuid" references="roles(id)"/>
            <field name="status" type="enum" values="active,suspended,pending" default="pending"/>
            <field name="invited_by" type="uuid" references="users(id)"/>
            <field name="invited_at" type="timestamptz"/>
            <field name="joined_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <unique fields="organization_id,user_id"/>
            <index fields="organization_id"/>
            <index fields="user_id"/>
        </entity>

        <entity name="roles">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)"/>
            <field name="name" type="varchar(50)" required="true"/>
            <field name="slug" type="varchar(50)" required="true"/>
            <field name="description" type="text"/>
            <field name="is_system" type="boolean" default="false"/>
            <field name="permissions" type="text[]"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="permissions">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="name" type="varchar(100)" required="true"/>
            <field name="description" type="text"/>
            <field name="resource" type="varchar(50)" required="true"/>
            <field name="action" type="varchar(20)" required="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="role_permissions">
            <field name="role_id" type="uuid" references="roles(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="permission_id" type="uuid" references="permissions(id)" on_delete="CASCADE" primary_key="true"/>
        </entity>

        <entity name="invitations">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)" on_delete="CASCADE" required="true"/>
            <field name="email" type="varchar(255)" required="true"/>
            <field name="role_id" type="uuid" references="roles(id)"/>
            <field name="token" type="varchar(100)" unique="true" required="true"/>
            <field name="invited_by" type="uuid" references="users(id)"/>
            <field name="status" type="enum" values="pending,accepted,expired,cancelled" default="pending"/>
            <field name="expires_at" type="timestamptz" required="true"/>
            <field name="accepted_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="plans">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="name" type="varchar(50)" required="true"/>
            <field name="slug" type="varchar(50)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="price_monthly" type="decimal(10,2)" required="true"/>
            <field name="price_yearly" type="decimal(10,2)"/>
            <field name="currency" type="char(3)" default="USD"/>
            <field name="features" type="jsonb"/>
            <field name="limits" type="jsonb"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="is_public" type="boolean" default="true"/>
            <field name="trial_days" type="integer" default="14"/>
            <field name="sort_order" type="integer" default="0"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="subscriptions">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)" on_delete="CASCADE" required="true"/>
            <field name="plan_id" type="uuid" references="plans(id)" required="true"/>
            <field name="status" type="enum" values="trialing,active,past_due,cancelled,paused" default="trialing"/>
            <field name="billing_cycle" type="enum" values="monthly,yearly"/>
            <field name="current_period_start" type="timestamptz" required="true"/>
            <field name="current_period_end" type="timestamptz" required="true"/>
            <field name="cancel_at_period_end" type="boolean" default="false"/>
            <field name="cancelled_at" type="timestamptz"/>
            <field name="trial_start" type="timestamptz"/>
            <field name="trial_end" type="timestamptz"/>
            <field name="payment_provider" type="varchar(50)"/>
            <field name="provider_subscription_id" type="varchar(255)"/>
            <field name="provider_customer_id" type="varchar(255)"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="status" partial="status IN ('active', 'trialing', 'past_due')"/>
        </entity>

        <entity name="invoices">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)" required="true"/>
            <field name="subscription_id" type="uuid" references="subscriptions(id)"/>
            <field name="invoice_number" type="varchar(50)" unique="true" required="true"/>
            <field name="status" type="enum" values="draft,open,paid,void,uncollectible" default="draft"/>
            <field name="currency" type="char(3)" required="true"/>
            <field name="subtotal" type="decimal(12,2)" required="true"/>
            <field name="tax" type="decimal(12,2)" default="0"/>
            <field name="total" type="decimal(12,2)" required="true"/>
            <field name="amount_paid" type="decimal(12,2)" default="0"/>
            <field name="amount_due" type="decimal(12,2)" required="true"/>
            <field name="billing_address" type="jsonb"/>
            <field name="lines" type="jsonb"/>
            <field name="provider_invoice_id" type="varchar(255)"/>
            <field name="provider_invoice_url" type="varchar(500)"/>
            <field name="period_start" type="timestamptz"/>
            <field name="period_end" type="timestamptz"/>
            <field name="due_date" type="timestamptz"/>
            <field name="paid_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="api_keys">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)" on_delete="CASCADE" required="true"/>
            <field name="user_id" type="uuid" references="users(id)"/>
            <field name="name" type="varchar(100)" required="true"/>
            <field name="key_prefix" type="varchar(10)" required="true"/>
            <field name="key_hash" type="varchar(255)" required="true"/>
            <field name="scopes" type="text[]"/>
            <field name="rate_limit" type="integer"/>
            <field name="last_used_at" type="timestamptz"/>
            <field name="expires_at" type="timestamptz"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="key_prefix"/>
        </entity>

        <entity name="usage_records">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)" on_delete="CASCADE" required="true"/>
            <field name="metric" type="varchar(50)" required="true"/>
            <field name="quantity" type="bigint" required="true"/>
            <field name="recorded_at" type="timestamptz" required="true"/>
            <field name="period_start" type="timestamptz" required="true"/>
            <field name="period_end" type="timestamptz" required="true"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="organization_id,metric,period_start"/>
        </entity>

        <entity name="audit_logs">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="organization_id" type="uuid" references="organizations(id)" on_delete="CASCADE" required="true"/>
            <field name="user_id" type="uuid" references="users(id)"/>
            <field name="action" type="varchar(100)" required="true"/>
            <field name="resource_type" type="varchar(50)"/>
            <field name="resource_id" type="uuid"/>
            <field name="old_values" type="jsonb"/>
            <field name="new_values" type="jsonb"/>
            <field name="ip_address" type="inet"/>
            <field name="user_agent" type="text"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="organization_id,created_at" order="DESC"/>
        </entity>
    </entities>

    <row_level_security>
        <policy table="ALL_TENANT_TABLES">
            <enable>ALTER TABLE {table} ENABLE ROW LEVEL SECURITY</enable>
            <create>CREATE POLICY org_isolation ON {table} USING (organization_id = current_setting('app.org_id')::UUID)</create>
        </policy>
    </row_level_security>
</saas_pattern>
"""