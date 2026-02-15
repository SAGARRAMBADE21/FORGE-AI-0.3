"""E-commerce database patterns."""
ECOMMERCE_XML = """
<ecommerce_pattern>
    <signals>
        <signal>products</signal><signal>SKU</signal><signal>inventory</signal>
        <signal>cart</signal><signal>checkout</signal><signal>orders</signal>
        <signal>payments</signal><signal>shipping</signal><signal>categories</signal>
        <signal>reviews</signal><signal>coupons</signal><signal>wishlist</signal>
    </signals>

    <entities>
        <entity name="users">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="email" type="varchar(255)" unique="true" required="true"/>
            <field name="password_hash" type="varchar(255)" required="true"/>
            <field name="first_name" type="varchar(50)"/>
            <field name="last_name" type="varchar(50)"/>
            <field name="phone" type="varchar(20)"/>
            <field name="role" type="enum" values="customer,admin,staff" default="customer"/>
            <field name="is_verified" type="boolean" default="false"/>
            <field name="last_login_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="addresses">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE"/>
            <field name="type" type="enum" values="shipping,billing"/>
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
            <index fields="user_id"/>
        </entity>

        <entity name="categories">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="parent_id" type="uuid" references="categories(id)" on_delete="CASCADE"/>
            <field name="name" type="varchar(100)" required="true"/>
            <field name="slug" type="varchar(100)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="image_url" type="varchar(500)"/>
            <field name="sort_order" type="integer" default="0"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="meta_title" type="varchar(255)"/>
            <field name="meta_description" type="text"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="parent_id"/>
            <index fields="slug"/>
        </entity>

        <entity name="products">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="sku" type="varchar(50)" unique="true" required="true"/>
            <field name="name" type="varchar(255)" required="true"/>
            <field name="slug" type="varchar(255)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="short_description" type="varchar(500)"/>
            <field name="price" type="decimal(10,2)" required="true"/>
            <field name="compare_at_price" type="decimal(10,2)"/>
            <field name="cost_price" type="decimal(10,2)"/>
            <field name="category_id" type="uuid" references="categories(id)"/>
            <field name="brand_id" type="uuid" references="brands(id)"/>
            <field name="status" type="enum" values="draft,active,archived" default="draft"/>
            <field name="is_featured" type="boolean" default="false"/>
            <field name="is_taxable" type="boolean" default="true"/>
            <field name="weight" type="decimal(10,3)"/>
            <field name="weight_unit" type="enum" values="kg,lb,g,oz"/>
            <field name="images" type="jsonb"/>
            <field name="metadata" type="jsonb"/>
            <field name="meta_title" type="varchar(255)"/>
            <field name="meta_description" type="text"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="category_id"/>
            <index fields="status" partial="status = 'active'"/>
            <index fields="slug"/>
            <index fields="sku"/>
        </entity>

        <entity name="product_variants">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="product_id" type="uuid" references="products(id)" on_delete="CASCADE" required="true"/>
            <field name="sku" type="varchar(50)" unique="true" required="true"/>
            <field name="name" type="varchar(255)"/>
            <field name="price" type="decimal(10,2)"/>
            <field name="compare_at_price" type="decimal(10,2)"/>
            <field name="options" type="jsonb"/>
            <field name="image_url" type="varchar(500)"/>
            <field name="position" type="integer" default="0"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="product_id"/>
        </entity>

        <entity name="inventory">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="product_id" type="uuid" references="products(id)"/>
            <field name="variant_id" type="uuid" references="product_variants(id)"/>
            <field name="location_id" type="uuid" references="locations(id)"/>
            <field name="quantity" type="integer" required="true" default="0"/>
            <field name="reserved" type="integer" required="true" default="0"/>
            <field name="low_stock_threshold" type="integer" default="10"/>
            <field name="track_inventory" type="boolean" default="true"/>
            <field name="allow_backorder" type="boolean" default="false"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <unique fields="product_id,variant_id,location_id"/>
            <index fields="product_id"/>
        </entity>

        <entity name="carts">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)"/>
            <field name="session_id" type="varchar(255)"/>
            <field name="currency_code" type="char(3)" default="USD"/>
            <field name="subtotal" type="decimal(12,2)" default="0"/>
            <field name="discount_total" type="decimal(12,2)" default="0"/>
            <field name="tax_total" type="decimal(12,2)" default="0"/>
            <field name="total" type="decimal(12,2)" default="0"/>
            <field name="coupon_code" type="varchar(50)"/>
            <field name="notes" type="text"/>
            <field name="metadata" type="jsonb"/>
            <field name="expires_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="user_id"/>
            <index fields="session_id"/>
        </entity>

        <entity name="cart_items">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="cart_id" type="uuid" references="carts(id)" on_delete="CASCADE" required="true"/>
            <field name="product_id" type="uuid" references="products(id)" required="true"/>
            <field name="variant_id" type="uuid" references="product_variants(id)"/>
            <field name="quantity" type="integer" required="true" default="1"/>
            <field name="unit_price" type="decimal(10,2)" required="true"/>
            <field name="total_price" type="decimal(12,2)" required="true"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="cart_id"/>
        </entity>

        <entity name="orders">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="order_number" type="varchar(50)" unique="true" required="true"/>
            <field name="user_id" type="uuid" references="users(id)"/>
            <field name="status" type="enum" values="pending,confirmed,processing,shipped,delivered,cancelled,refunded" default="pending"/>
            <field name="payment_status" type="enum" values="pending,authorized,paid,partially_refunded,refunded,failed" default="pending"/>
            <field name="fulfillment_status" type="enum" values="unfulfilled,partial,fulfilled" default="unfulfilled"/>
            <field name="currency_code" type="char(3)" required="true"/>
            <field name="subtotal" type="decimal(12,2)" required="true"/>
            <field name="discount_total" type="decimal(12,2)" default="0"/>
            <field name="shipping_total" type="decimal(12,2)" default="0"/>
            <field name="tax_total" type="decimal(12,2)" default="0"/>
            <field name="grand_total" type="decimal(12,2)" required="true"/>
            <field name="total_paid" type="decimal(12,2)" default="0"/>
            <field name="total_refunded" type="decimal(12,2)" default="0"/>
            <field name="shipping_address" type="jsonb" required="true"/>
            <field name="billing_address" type="jsonb" required="true"/>
            <field name="shipping_method" type="varchar(100)"/>
            <field name="tracking_number" type="varchar(100)"/>
            <field name="tracking_url" type="varchar(500)"/>
            <field name="coupon_code" type="varchar(50)"/>
            <field name="customer_notes" type="text"/>
            <field name="internal_notes" type="text"/>
            <field name="metadata" type="jsonb"/>
            <field name="placed_at" type="timestamptz"/>
            <field name="shipped_at" type="timestamptz"/>
            <field name="delivered_at" type="timestamptz"/>
            <field name="cancelled_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="user_id"/>
            <index fields="status"/>
            <index fields="created_at" order="DESC"/>
            <index fields="order_number"/>
        </entity>

        <entity name="order_items">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="order_id" type="uuid" references="orders(id)" on_delete="CASCADE" required="true"/>
            <field name="product_id" type="uuid" references="products(id)"/>
            <field name="variant_id" type="uuid" references="product_variants(id)"/>
            <field name="sku" type="varchar(50)" required="true"/>
            <field name="name" type="varchar(255)" required="true"/>
            <field name="quantity" type="integer" required="true"/>
            <field name="unit_price" type="decimal(10,2)" required="true"/>
            <field name="discount" type="decimal(10,2)" default="0"/>
            <field name="tax" type="decimal(10,2)" default="0"/>
            <field name="total" type="decimal(12,2)" required="true"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="order_id"/>
        </entity>

        <entity name="payments">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="order_id" type="uuid" references="orders(id)" on_delete="CASCADE" required="true"/>
            <field name="payment_method" type="varchar(50)" required="true"/>
            <field name="payment_provider" type="varchar(50)"/>
            <field name="provider_transaction_id" type="varchar(255)"/>
            <field name="status" type="enum" values="pending,authorized,captured,failed,refunded" default="pending"/>
            <field name="amount" type="decimal(12,2)" required="true"/>
            <field name="currency_code" type="char(3)" required="true"/>
            <field name="refunded_amount" type="decimal(12,2)" default="0"/>
            <field name="metadata" type="jsonb"/>
            <field name="processed_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="order_id"/>
        </entity>

        <entity name="reviews">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="product_id" type="uuid" references="products(id)" on_delete="CASCADE" required="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="order_id" type="uuid" references="orders(id)"/>
            <field name="rating" type="smallint" required="true" check="rating >= 1 AND rating <= 5"/>
            <field name="title" type="varchar(255)"/>
            <field name="content" type="text"/>
            <field name="pros" type="text[]"/>
            <field name="cons" type="text[]"/>
            <field name="is_verified_purchase" type="boolean" default="false"/>
            <field name="is_approved" type="boolean" default="false"/>
            <field name="helpful_count" type="integer" default="0"/>
            <field name="images" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="product_id"/>
            <index fields="product_id,rating"/>
        </entity>

        <entity name="coupons">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="code" type="varchar(50)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="type" type="enum" values="percentage,fixed_amount,free_shipping"/>
            <field name="value" type="decimal(10,2)" required="true"/>
            <field name="minimum_order" type="decimal(10,2)"/>
            <field name="maximum_discount" type="decimal(10,2)"/>
            <field name="usage_limit" type="integer"/>
            <field name="usage_count" type="integer" default="0"/>
            <field name="per_user_limit" type="integer" default="1"/>
            <field name="applicable_products" type="uuid[]"/>
            <field name="applicable_categories" type="uuid[]"/>
            <field name="starts_at" type="timestamptz"/>
            <field name="expires_at" type="timestamptz"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="code"/>
        </entity>

        <entity name="wishlists">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="name" type="varchar(100)" default="My Wishlist"/>
            <field name="is_public" type="boolean" default="false"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="user_id"/>
        </entity>

        <entity name="wishlist_items">
            <field name="wishlist_id" type="uuid" references="wishlists(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="product_id" type="uuid" references="products(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="variant_id" type="uuid" references="product_variants(id)"/>
            <field name="added_at" type="timestamptz" default="NOW()"/>
        </entity>
    </entities>

    <relationships>
        <relationship type="one_to_many" from="users" to="addresses"/>
        <relationship type="one_to_many" from="users" to="orders"/>
        <relationship type="one_to_many" from="users" to="reviews"/>
        <relationship type="one_to_many" from="categories" to="categories" self="true"/>
        <relationship type="one_to_many" from="categories" to="products"/>
        <relationship type="one_to_many" from="products" to="product_variants"/>
        <relationship type="one_to_many" from="products" to="reviews"/>
        <relationship type="one_to_many" from="orders" to="order_items"/>
        <relationship type="one_to_many" from="orders" to="payments"/>
        <relationship type="many_to_many" from="users" to="products" through="wishlists"/>
    </relationships>
</ecommerce_pattern>
"""