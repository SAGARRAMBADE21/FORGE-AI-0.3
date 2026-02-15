"""Content management database patterns."""
CONTENT_XML = """
<content_pattern>
    <signals>
        <signal>articles</signal><signal>posts</signal><signal>blogs</signal>
        <signal>pages</signal><signal>categories</signal><signal>tags</signal>
        <signal>authors</signal><signal>comments</signal><signal>media</signal>
        <signal>publish</signal><signal>draft</signal><signal>revisions</signal>
    </signals>

    <entities>
        <entity name="users">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="email" type="varchar(255)" unique="true" required="true"/>
            <field name="password_hash" type="varchar(255)" required="true"/>
            <field name="name" type="varchar(100)"/>
            <field name="slug" type="varchar(100)" unique="true"/>
            <field name="bio" type="text"/>
            <field name="avatar_url" type="varchar(500)"/>
            <field name="role" type="enum" values="admin,editor,author,contributor" default="contributor"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="categories">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="parent_id" type="uuid" references="categories(id)" on_delete="CASCADE"/>
            <field name="name" type="varchar(100)" required="true"/>
            <field name="slug" type="varchar(100)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="image_url" type="varchar(500)"/>
            <field name="sort_order" type="integer" default="0"/>
            <field name="post_count" type="integer" default="0"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="parent_id"/>
            <index fields="slug"/>
        </entity>

        <entity name="tags">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="name" type="varchar(50)" required="true"/>
            <field name="slug" type="varchar(50)" unique="true" required="true"/>
            <field name="description" type="text"/>
            <field name="post_count" type="integer" default="0"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="articles">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="title" type="varchar(255)" required="true"/>
            <field name="slug" type="varchar(255)" unique="true" required="true"/>
            <field name="excerpt" type="varchar(500)"/>
            <field name="content" type="text"/>
            <field name="content_html" type="text"/>
            <field name="featured_image" type="varchar(500)"/>
            <field name="author_id" type="uuid" references="users(id)" required="true"/>
            <field name="category_id" type="uuid" references="categories(id)"/>
            <field name="status" type="enum" values="draft,pending,published,scheduled,archived" default="draft"/>
            <field name="visibility" type="enum" values="public,private,password_protected" default="public"/>
            <field name="password" type="varchar(255)"/>
            <field name="is_featured" type="boolean" default="false"/>
            <field name="is_pinned" type="boolean" default="false"/>
            <field name="allow_comments" type="boolean" default="true"/>
            <field name="view_count" type="integer" default="0"/>
            <field name="like_count" type="integer" default="0"/>
            <field name="comment_count" type="integer" default="0"/>
            <field name="reading_time" type="integer"/>
            <field name="meta_title" type="varchar(255)"/>
            <field name="meta_description" type="text"/>
            <field name="og_image" type="varchar(500)"/>
            <field name="published_at" type="timestamptz"/>
            <field name="scheduled_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="author_id"/>
            <index fields="category_id"/>
            <index fields="status,published_at" order="DESC" partial="status = 'published'"/>
            <index fields="slug"/>
        </entity>

        <entity name="article_tags">
            <field name="article_id" type="uuid" references="articles(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="tag_id" type="uuid" references="tags(id)" on_delete="CASCADE" primary_key="true"/>
        </entity>

        <entity name="article_revisions">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="article_id" type="uuid" references="articles(id)" on_delete="CASCADE" required="true"/>
            <field name="title" type="varchar(255)"/>
            <field name="content" type="text"/>
            <field name="revision_number" type="integer" required="true"/>
            <field name="created_by" type="uuid" references="users(id)"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <index fields="article_id"/>
        </entity>

        <entity name="comments">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="article_id" type="uuid" references="articles(id)" on_delete="CASCADE" required="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="SET NULL"/>
            <field name="parent_id" type="uuid" references="comments(id)" on_delete="CASCADE"/>
            <field name="author_name" type="varchar(100)"/>
            <field name="author_email" type="varchar(255)"/>
            <field name="content" type="text" required="true"/>
            <field name="status" type="enum" values="pending,approved,spam,trash" default="pending"/>
            <field name="ip_address" type="inet"/>
            <field name="user_agent" type="text"/>
            <field name="like_count" type="integer" default="0"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="article_id"/>
            <index fields="status" partial="status = 'approved'"/>
        </entity>

        <entity name="media">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)"/>
            <field name="filename" type="varchar(255)" required="true"/>
            <field name="original_filename" type="varchar(255)"/>
            <field name="mime_type" type="varchar(100)"/>
            <field name="file_size" type="bigint"/>
            <field name="url" type="varchar(500)" required="true"/>
            <field name="thumbnail_url" type="varchar(500)"/>
            <field name="alt_text" type="varchar(255)"/>
            <field name="caption" type="text"/>
            <field name="width" type="integer"/>
            <field name="height" type="integer"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="pages">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="title" type="varchar(255)" required="true"/>
            <field name="slug" type="varchar(255)" unique="true" required="true"/>
            <field name="content" type="text"/>
            <field name="parent_id" type="uuid" references="pages(id)"/>
            <field name="template" type="varchar(100)"/>
            <field name="status" type="enum" values="draft,published" default="draft"/>
            <field name="sort_order" type="integer" default="0"/>
            <field name="meta_title" type="varchar(255)"/>
            <field name="meta_description" type="text"/>
            <field name="author_id" type="uuid" references="users(id)"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
        </entity>
    </entities>

    <fulltext_search>
        <postgresql>
            <column>ALTER TABLE articles ADD COLUMN search_vector TSVECTOR</column>
            <index>CREATE INDEX idx_articles_search ON articles USING GIN(search_vector)</index>
            <trigger>
CREATE TRIGGER articles_search_update BEFORE INSERT OR UPDATE ON articles
FOR EACH ROW EXECUTE FUNCTION tsvector_update_trigger(search_vector, 'pg_catalog.english', title, content)
            </trigger>
        </postgresql>
    </fulltext_search>
</content_pattern>
"""