"""Database relationships knowledge base."""
RELATIONSHIPS_XML = """
<relationships>
    <one_to_one cardinality="1:1">
        <description>Each row in table A relates to exactly one row in table B</description>
        <use_cases>
            <use_case>Separating rarely accessed data</use_case>
            <use_case>Optional extension data (profiles, settings)</use_case>
            <use_case>Security separation (sensitive data)</use_case>
        </use_cases>
        <implementation name="unique_foreign_key">
            <sql>
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);

CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    avatar_url VARCHAR(500)
);
            </sql>
        </implementation>
        <implementation name="shared_primary_key">
            <sql>
CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'light',
    notifications_enabled BOOLEAN DEFAULT true
);
            </sql>
        </implementation>
    </one_to_one>

    <one_to_many cardinality="1:N">
        <description>One row in table A relates to many rows in table B</description>
        <use_cases>
            <use_case>User has many orders</use_case>
            <use_case>Post has many comments</use_case>
            <use_case>Category has many products</use_case>
        </use_cases>
        <implementation>
            <sql>
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CRITICAL: Always index foreign keys
CREATE INDEX idx_orders_user_id ON orders(user_id);
            </sql>
        </implementation>
        <mongodb>
            <embedding desc="For bounded, always-accessed-together data">
{
    _id: ObjectId(),
    email: "user@example.com",
    addresses: [
        {type: "home", street: "123 Main"},
        {type: "work", street: "456 Office"}
    ]
}
            </embedding>
            <referencing desc="For unbounded or independently-accessed data">
// users collection
{_id: ObjectId("user1"), email: "user@example.com"}

// orders collection
{_id: ObjectId(), user_id: ObjectId("user1"), total: 99.99}
            </referencing>
        </mongodb>
    </one_to_many>

    <many_to_many cardinality="M:N">
        <description>Multiple rows in A relate to multiple rows in B</description>
        <use_cases>
            <use_case>Users have many roles</use_case>
            <use_case>Products have many categories</use_case>
            <use_case>Students have many courses</use_case>
        </use_cases>
        <implementation name="junction_table">
            <sql>
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Index both directions
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
            </sql>
        </implementation>
        <implementation name="junction_with_attributes">
            <sql>
CREATE TABLE product_categories (
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT false,
    sort_order INT DEFAULT 0,
    PRIMARY KEY (product_id, category_id)
);

-- Ensure only one primary category per product
CREATE UNIQUE INDEX idx_product_primary_category 
ON product_categories(product_id) WHERE is_primary = true;
            </sql>
        </implementation>
        <mongodb>
            <array_of_references>
// products collection
{
    _id: ObjectId(),
    name: "Laptop",
    category_ids: [ObjectId("cat1"), ObjectId("cat2")]
}
            </array_of_references>
        </mongodb>
    </many_to_many>

    <self_referencing>
        <hierarchical name="tree_structure">
            <use_cases>Categories, organizational charts, comment threads</use_cases>
            <sql>
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    parent_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    depth INT DEFAULT 0,
    path TEXT -- '/root/parent/child' for fast queries
);

CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_path ON categories(path);
            </sql>
        </hierarchical>
        
        <social name="follower_following">
            <sql>
CREATE TABLE follows (
    follower_id UUID REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, following_id),
    CHECK (follower_id != following_id)
);

CREATE INDEX idx_follows_follower ON follows(follower_id);
CREATE INDEX idx_follows_following ON follows(following_id);
            </sql>
        </social>
        
        <manager name="employee_manager">
            <sql>
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    manager_id UUID REFERENCES employees(id) ON DELETE SET NULL
);

CREATE INDEX idx_employees_manager ON employees(manager_id);
            </sql>
        </manager>
    </self_referencing>

    <polymorphic>
        <option name="separate_tables" recommended="yes">
            <description>Separate table per type - maintains referential integrity</description>
            <sql>
CREATE TABLE post_comments (
    id UUID PRIMARY KEY,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    content TEXT NOT NULL
);

CREATE TABLE product_comments (
    id UUID PRIMARY KEY,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    content TEXT NOT NULL
);
            </sql>
        </option>

        <option name="type_column">
            <description>Single table with type discriminator - no FK constraint</description>
            <sql>
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commentable_type VARCHAR(50) NOT NULL,
    commentable_id UUID NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_target ON comments(commentable_type, commentable_id);
            </sql>
        </option>

        <option name="multiple_fks">
            <description>Multiple nullable FKs - maintains constraints</description>
            <sql>
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    CHECK (
        (post_id IS NOT NULL)::INT +
        (product_id IS NOT NULL)::INT +
        (article_id IS NOT NULL)::INT = 1
    )
);
            </sql>
        </option>
    </polymorphic>
</relationships>
"""
