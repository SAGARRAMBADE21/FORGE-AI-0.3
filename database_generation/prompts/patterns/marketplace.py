"""Marketplace database patterns."""
MARKETPLACE_XML = """
<marketplace_pattern>
    <signals>
        <signal>listings</signal><signal>sellers</signal><signal>buyers</signal>
        <signal>bids</signal><signal>offers</signal><signal>transactions</signal>
        <signal>reviews</signal><signal>commissions</signal><signal>payouts</signal>
        <signal>disputes</signal><signal>favorites</signal>
    </signals>

    <entities>
        <entity name="users">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="email" type="varchar(255)" unique="true" required="true"/>
            <field name="password_hash" type="varchar(255)" required="true"/>
            <field name="name" type="varchar(100)"/>
            <field name="avatar_url" type="varchar(500)"/>
            <field name="phone" type="varchar(20)"/>
            <field name="is_verified" type="boolean" default="false"/>
            <field name="is_seller" type="boolean" default="false"/>
            <field name="rating" type="decimal(2,1)" default="0"/>
            <field name="review_count" type="integer" default="0"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="seller_profiles">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" unique="true" required="true"/>
            <field name="business_name" type="varchar(100)"/>
            <field name="slug" type="varchar(100)" unique="true"/>
            <field name="description" type="text"/>
            <field name="logo_url" type="varchar(500)"/>
            <field name="banner_url" type="varchar(500)"/>
            <field name="location" type="varchar(100)"/>
            <field name="website" type="varchar(255)"/>
            <field name="rating" type="decimal(2,1)" default="0"/>
            <field name="review_count" type="integer" default="0"/>
            <field name="listing_count" type="integer" default="0"/>
            <field name="sales_count" type="integer" default="0"/>
            <field name="total_revenue" type="decimal(12,2)" default="0"/>
            <field name="commission_rate" type="decimal(4,2)" default="10.00"/>
            <field name="is_verified" type="boolean" default="false"/>
            <field name="verified_at" type="timestamptz"/>
            <field name="settings" type="jsonb" default="'{}'"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="categories">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="parent_id" type="uuid" references="categories(id)"/>
            <field name="name" type="varchar(100)" required="true"/>
            <field name="slug" type="varchar(100)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="image_url" type="varchar(500)"/>
            <field name="commission_rate" type="decimal(4,2)"/>
            <field name="listing_count" type="integer" default="0"/>
            <field name="sort_order" type="integer" default="0"/>
            <field name="is_active" type="boolean" default="true"/>
        </entity>

        <entity name="listings">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="seller_id" type="uuid" references="seller_profiles(id)" on_delete="CASCADE" required="true"/>
            <field name="category_id" type="uuid" references="categories(id)"/>
            <field name="title" type="varchar(255)" required="true"/>
            <field name="slug" type="varchar(255)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="condition" type="enum" values="new,like_new,good,fair,poor"/>
            <field name="price" type="decimal(12,2)" required="true"/>
            <field name="original_price" type="decimal(12,2)"/>
            <field name="currency" type="char(3)" default="USD"/>
            <field name="quantity" type="integer" default="1"/>
            <field name="quantity_sold" type="integer" default="0"/>
            <field name="listing_type" type="enum" values="fixed,auction,offer" default="fixed"/>
            <field name="auction_end_at" type="timestamptz"/>
            <field name="min_offer" type="decimal(12,2)"/>
            <field name="allow_offers" type="boolean" default="false"/>
            <field name="images" type="jsonb"/>
            <field name="attributes" type="jsonb"/>
            <field name="location" type="varchar(100)"/>
            <field name="shipping_options" type="jsonb"/>
            <field name="status" type="enum" values="draft,active,sold,expired,cancelled" default="draft"/>
            <field name="view_count" type="integer" default="0"/>
            <field name="favorite_count" type="integer" default="0"/>
            <field name="featured_until" type="timestamptz"/>
            <field name="expires_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="seller_id"/>
            <index fields="category_id"/>
            <index fields="status,created_at" order="DESC" partial="status = 'active'"/>
            <index fields="price" partial="status = 'active'"/>
        </entity>

        <entity name="bids">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="listing_id" type="uuid" references="listings(id)" on_delete="CASCADE" required="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="amount" type="decimal(12,2)" required="true"/>
            <field name="max_amount" type="decimal(12,2)"/>
            <field name="is_winning" type="boolean" default="false"/>
            <field name="is_auto" type="boolean" default="false"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="listing_id,amount" order="DESC"/>
        </entity>

        <entity name="offers">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="listing_id" type="uuid" references="listings(id)" on_delete="CASCADE" required="true"/>
            <field name="buyer_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="amount" type="decimal(12,2)" required="true"/>
            <field name="message" type="text"/>
            <field name="status" type="enum" values="pending,accepted,rejected,expired,withdrawn" default="pending"/>
            <field name="expires_at" type="timestamptz"/>
            <field name="responded_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="favorites">
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="listing_id" type="uuid" references="listings(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="transactions">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="transaction_number" type="varchar(50)" unique="true" required="true"/>
            <field name="listing_id" type="uuid" references="listings(id)"/>
            <field name="seller_id" type="uuid" references="users(id)"/>
            <field name="buyer_id" type="uuid" references="users(id)"/>
            <field name="quantity" type="integer" required="true" default="1"/>
            <field name="unit_price" type="decimal(12,2)" required="true"/>
            <field name="subtotal" type="decimal(12,2)" required="true"/>
            <field name="shipping_cost" type="decimal(12,2)" default="0"/>
            <field name="tax" type="decimal(12,2)" default="0"/>
            <field name="platform_fee" type="decimal(12,2)" required="true"/>
            <field name="seller_amount" type="decimal(12,2)" required="true"/>
            <field name="total" type="decimal(12,2)" required="true"/>
            <field name="currency" type="char(3)" required="true"/>
            <field name="status" type="enum" values="pending,paid,shipped,delivered,completed,cancelled,refunded,disputed" default="pending"/>
            <field name="payment_method" type="varchar(50)"/>
            <field name="payment_id" type="varchar(255)"/>
            <field name="shipping_address" type="jsonb"/>
            <field name="tracking_number" type="varchar(100)"/>
            <field name="tracking_url" type="varchar(500)"/>
            <field name="notes" type="text"/>
            <field name="paid_at" type="timestamptz"/>
            <field name="shipped_at" type="timestamptz"/>
            <field name="delivered_at" type="timestamptz"/>
            <field name="completed_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="seller_id"/>
            <index fields="buyer_id"/>
        </entity>

        <entity name="reviews">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="transaction_id" type="uuid" references="transactions(id)"/>
            <field name="reviewer_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="reviewee_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="listing_id" type="uuid" references="listings(id)"/>
            <field name="type" type="enum" values="buyer_to_seller,seller_to_buyer"/>
            <field name="rating" type="smallint" required="true" check="rating >= 1 AND rating <= 5"/>
            <field name="title" type="varchar(255)"/>
            <field name="content" type="text"/>
            <field name="response" type="text"/>
            <field name="response_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="reviewee_id"/>
        </entity>

        <entity name="payouts">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="seller_id" type="uuid" references="seller_profiles(id)" on_delete="CASCADE" required="true"/>
            <field name="amount" type="decimal(12,2)" required="true"/>
            <field name="currency" type="char(3)" required="true"/>
            <field name="status" type="enum" values="pending,processing,completed,failed" default="pending"/>
            <field name="method" type="varchar(50)"/>
            <field name="reference" type="varchar(255)"/>
            <field name="period_start" type="timestamptz"/>
            <field name="period_end" type="timestamptz"/>
            <field name="transaction_count" type="integer"/>
            <field name="processed_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="disputes">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="transaction_id" type="uuid" references="transactions(id)" required="true"/>
            <field name="opened_by" type="uuid" references="users(id)" required="true"/>
            <field name="reason" type="enum" values="not_received,not_as_described,damaged,other"/>
            <field name="description" type="text"/>
            <field name="status" type="enum" values="open,under_review,resolved,escalated,closed" default="open"/>
            <field name="resolution" type="text"/>
            <field name="resolved_by" type="uuid" references="users(id)"/>
            <field name="resolved_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>
    </entities>
</marketplace_pattern>
"""