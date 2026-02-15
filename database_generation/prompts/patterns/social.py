"""Social media database patterns."""
SOCIAL_XML = """
<social_pattern>
    <signals>
        <signal>posts</signal><signal>tweets</signal><signal>comments</signal>
        <signal>likes</signal><signal>follows</signal><signal>followers</signal>
        <signal>feed</signal><signal>timeline</signal><signal>notifications</signal>
        <signal>messages</signal><signal>hashtags</signal><signal>mentions</signal>
    </signals>

    <entities>
        <entity name="users">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="username" type="varchar(30)" unique="true" required="true"/>
            <field name="email" type="varchar(255)" unique="true" required="true"/>
            <field name="password_hash" type="varchar(255)" required="true"/>
            <field name="display_name" type="varchar(100)"/>
            <field name="bio" type="varchar(500)"/>
            <field name="avatar_url" type="varchar(500)"/>
            <field name="cover_url" type="varchar(500)"/>
            <field name="location" type="varchar(100)"/>
            <field name="website" type="varchar(255)"/>
            <field name="date_of_birth" type="date"/>
            <field name="is_verified" type="boolean" default="false"/>
            <field name="is_private" type="boolean" default="false"/>
            <field name="is_active" type="boolean" default="true"/>
            <field name="follower_count" type="integer" default="0"/>
            <field name="following_count" type="integer" default="0"/>
            <field name="post_count" type="integer" default="0"/>
            <field name="settings" type="jsonb" default="'{}'"/>
            <field name="last_active_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <index fields="username"/>
        </entity>

        <entity name="follows">
            <field name="follower_id" type="uuid" references="users(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="following_id" type="uuid" references="users(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <check>follower_id != following_id</check>
            <index fields="follower_id"/>
            <index fields="following_id"/>
        </entity>

        <entity name="blocks">
            <field name="blocker_id" type="uuid" references="users(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="blocked_id" type="uuid" references="users(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <check>blocker_id != blocked_id</check>
        </entity>

        <entity name="posts">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="parent_id" type="uuid" references="posts(id)"/>
            <field name="quoted_post_id" type="uuid" references="posts(id)"/>
            <field name="type" type="enum" values="post,reply,repost,quote" default="post"/>
            <field name="content" type="text"/>
            <field name="media" type="jsonb"/>
            <field name="mentions" type="uuid[]"/>
            <field name="hashtags" type="text[]"/>
            <field name="visibility" type="enum" values="public,followers,mentioned,private" default="public"/>
            <field name="is_pinned" type="boolean" default="false"/>
            <field name="like_count" type="integer" default="0"/>
            <field name="comment_count" type="integer" default="0"/>
            <field name="repost_count" type="integer" default="0"/>
            <field name="view_count" type="integer" default="0"/>
            <field name="metadata" type="jsonb"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <field name="deleted_at" type="timestamptz"/>
            <index fields="user_id,created_at" order="DESC"/>
            <index fields="visibility,created_at" order="DESC" partial="deleted_at IS NULL"/>
            <index fields="hashtags" type="GIN"/>
            <index fields="parent_id" partial="parent_id IS NOT NULL"/>
        </entity>

        <entity name="likes">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="post_id" type="uuid" references="posts(id)" on_delete="CASCADE" required="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <unique fields="user_id,post_id"/>
            <index fields="post_id"/>
            <index fields="user_id"/>
        </entity>

        <entity name="reposts">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="post_id" type="uuid" references="posts(id)" on_delete="CASCADE" required="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <unique fields="user_id,post_id"/>
        </entity>

        <entity name="bookmarks">
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="post_id" type="uuid" references="posts(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="hashtags">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="name" type="varchar(100)" unique="true" required="true"/>
            <field name="post_count" type="integer" default="0"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="post_hashtags">
            <field name="post_id" type="uuid" references="posts(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="hashtag_id" type="uuid" references="hashtags(id)" on_delete="CASCADE" primary_key="true"/>
        </entity>

        <entity name="notifications">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" required="true"/>
            <field name="actor_id" type="uuid" references="users(id)" on_delete="CASCADE"/>
            <field name="type" type="enum" values="like,comment,follow,mention,repost,quote"/>
            <field name="reference_type" type="varchar(50)"/>
            <field name="reference_id" type="uuid"/>
            <field name="content" type="text"/>
            <field name="is_read" type="boolean" default="false"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="read_at" type="timestamptz"/>
            <index fields="user_id,created_at" order="DESC" partial="is_read = FALSE"/>
            <index fields="user_id,created_at" order="DESC"/>
        </entity>

        <entity name="conversations">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="type" type="enum" values="direct,group" default="direct"/>
            <field name="name" type="varchar(100)"/>
            <field name="created_by" type="uuid" references="users(id)"/>
            <field name="last_message_at" type="timestamptz"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
        </entity>

        <entity name="conversation_participants">
            <field name="conversation_id" type="uuid" references="conversations(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="user_id" type="uuid" references="users(id)" on_delete="CASCADE" primary_key="true"/>
            <field name="role" type="enum" values="admin,member" default="member"/>
            <field name="last_read_at" type="timestamptz"/>
            <field name="is_muted" type="boolean" default="false"/>
            <field name="joined_at" type="timestamptz" default="NOW()"/>
            <field name="left_at" type="timestamptz"/>
        </entity>

        <entity name="messages">
            <field name="id" type="uuid" primary_key="true"/>
            <field name="conversation_id" type="uuid" references="conversations(id)" on_delete="CASCADE" required="true"/>
            <field name="sender_id" type="uuid" references="users(id)" on_delete="SET NULL"/>
            <field name="content" type="text"/>
            <field name="media" type="jsonb"/>
            <field name="type" type="enum" values="text,image,video,audio,file" default="text"/>
            <field name="is_edited" type="boolean" default="false"/>
            <field name="created_at" type="timestamptz" default="NOW()"/>
            <field name="updated_at" type="timestamptz" default="NOW()"/>
            <field name="deleted_at" type="timestamptz"/>
            <index fields="conversation_id,created_at" order="DESC"/>
        </entity>
    </entities>

    <relationships>
        <relationship type="many_to_many" from="users" to="users" through="follows" as="follower_following"/>
        <relationship type="many_to_many" from="users" to="users" through="blocks" as="blocker_blocked"/>
        <relationship type="one_to_many" from="users" to="posts"/>
        <relationship type="one_to_many" from="posts" to="posts" self="true" as="replies"/>
        <relationship type="many_to_many" from="users" to="posts" through="likes"/>
        <relationship type="many_to_many" from="posts" to="hashtags" through="post_hashtags"/>
        <relationship type="one_to_many" from="users" to="notifications"/>
        <relationship type="many_to_many" from="users" to="conversations" through="conversation_participants"/>
        <relationship type="one_to_many" from="conversations" to="messages"/>
    </relationships>
</social_pattern>
"""