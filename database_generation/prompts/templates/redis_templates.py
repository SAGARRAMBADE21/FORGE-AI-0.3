REDIS_TEMPLATE_XML = """
<redis_templates>
    <header>
        <![CDATA[
# =============================================
# FORGE Generated Schema
# Database: Redis
# Generated: {timestamp}
# =============================================
#
# Redis is schema-less. This file documents:
# - Key naming conventions
# - Data structure patterns
# - Index strategies using sorted sets
# - Recommended commands for each entity
# =============================================
        ]]>
    </header>

    <key_patterns>
        <pattern name="entity">
            <format>{entity}:{id}</format>
            <example>user:123e4567-e89b-12d3-a456-426614174000</example>
            <description>Primary key pattern for entity storage</description>
        </pattern>
        <pattern name="entity_field">
            <format>{entity}:{id}:{field}</format>
            <example>user:123:sessions</example>
            <description>Sub-key for entity collections or specific fields</description>
        </pattern>
        <pattern name="index">
            <format>{entity}:idx:{field}</format>
            <example>user:idx:email</example>
            <description>Secondary index using sorted set or set</description>
        </pattern>
        <pattern name="counter">
            <format>{entity}:{id}:count:{metric}</format>
            <example>post:456:count:likes</example>
            <description>Counter for entity metrics</description>
        </pattern>
        <pattern name="list">
            <format>{entity}:{id}:{relationship}</format>
            <example>user:123:followers</example>
            <description>List or set of related entity IDs</description>
        </pattern>
        <pattern name="sorted">
            <format>{entity}:by:{sort_field}</format>
            <example>posts:by:created_at</example>
            <description>Sorted set for ordered queries</description>
        </pattern>
        <pattern name="cache">
            <format>cache:{entity}:{id}</format>
            <example>cache:product:789</example>
            <description>Cached data with TTL</description>
        </pattern>
        <pattern name="session">
            <format>session:{token}</format>
            <example>session:abc123def456</example>
            <description>Session data storage</description>
        </pattern>
        <pattern name="lock">
            <format>lock:{resource}:{id}</format>
            <example>lock:order:456</example>
            <description>Distributed lock</description>
        </pattern>
        <pattern name="rate_limit">
            <format>rate:{action}:{identifier}:{window}</format>
            <example>rate:api:user123:minute</example>
            <description>Rate limiting counter</description>
        </pattern>
    </key_patterns>

    <entity_template>
        <![CDATA[
# =============================================
# Entity: {entity_name}
# =============================================

# Primary storage (Hash)
# Key: {entity}:{id}
# Type: HASH
# Fields: {field_list}

# Commands:
# Create/Update: HSET {entity}:{id} {field} {value} ...
# Read: HGETALL {entity}:{id}
# Read field: HGET {entity}:{id} {field}
# Delete: DEL {entity}:{id}
# Check exists: EXISTS {entity}:{id}

# Secondary Indexes:
{index_definitions}

# Relationships:
{relationship_definitions}
        ]]>
    </entity_template>

    <index_templates>
        <unique_index>
            <![CDATA[
# Unique index: {entity} by {field}
# Key: {entity}:idx:{field}
# Type: HASH (field -> id mapping)
# Set: HSET {entity}:idx:{field} {field_value} {id}
# Get: HGET {entity}:idx:{field} {field_value}
# Delete: HDEL {entity}:idx:{field} {field_value}
            ]]>
        </unique_index>
        <sorted_index>
            <![CDATA[
# Sorted index: {entity} by {field}
# Key: {entity}:by:{field}
# Type: SORTED SET (score = {field}, member = {id})
# Add: ZADD {entity}:by:{field} {score} {id}
# Range: ZRANGEBYSCORE {entity}:by:{field} {min} {max}
# Top N: ZREVRANGE {entity}:by:{field} 0 {n-1}
# Remove: ZREM {entity}:by:{field} {id}
            ]]>
        </sorted_index>
        <set_index>
            <![CDATA[
# Set index: {entity} by {field}
# Key: {entity}:{field}:{value}
# Type: SET
# Add: SADD {entity}:{field}:{value} {id}
# Members: SMEMBERS {entity}:{field}:{value}
# Remove: SREM {entity}:{field}:{value} {id}
# Count: SCARD {entity}:{field}:{value}
            ]]>
        </set_index>
    </index_templates>

    <relationship_templates>
        <one_to_many>
            <![CDATA[
# Relationship: {parent} has many {children}
# Key: {parent}:{parent_id}:{children}
# Type: SET or SORTED SET
# Add: SADD {parent}:{parent_id}:{children} {child_id}
# Get all: SMEMBERS {parent}:{parent_id}:{children}
# Count: SCARD {parent}:{parent_id}:{children}
# Remove: SREM {parent}:{parent_id}:{children} {child_id}
            ]]>
        </one_to_many>
        <many_to_many>
            <![CDATA[
# Relationship: {entity1} <-> {entity2}
# Keys: 
#   {entity1}:{id}:{entity2}s (SET of {entity2} IDs)
#   {entity2}:{id}:{entity1}s (SET of {entity1} IDs)
# Add (bidirectional):
#   SADD {entity1}:{id1}:{entity2}s {id2}
#   SADD {entity2}:{id2}:{entity1}s {id1}
# Remove (bidirectional):
#   SREM {entity1}:{id1}:{entity2}s {id2}
#   SREM {entity2}:{id2}:{entity1}s {id1}
            ]]>
        </many_to_many>
    </relationship_templates>

    <pattern_templates>
        <session_pattern>
            <![CDATA[
# Session Management
# Key: session:{token}
# Type: HASH
# TTL: {session_ttl} seconds

# Create session:
HSET session:{token} user_id {user_id} created_at {timestamp} data {json_data}
EXPIRE session:{token} {session_ttl}

# Get session:
HGETALL session:{token}

# Refresh session:
EXPIRE session:{token} {session_ttl}

# Delete session:
DEL session:{token}

# User sessions index:
SADD user:{user_id}:sessions {token}
SREM user:{user_id}:sessions {token}
            ]]>
        </session_pattern>

        <cache_pattern>
            <![CDATA[
# Cache Pattern
# Key: cache:{entity}:{id}
# Type: STRING (JSON) or HASH
# TTL: {cache_ttl} seconds

# Set cache:
SET cache:{entity}:{id} {json_data} EX {cache_ttl}

# Get cache:
GET cache:{entity}:{id}

# Invalidate:
DEL cache:{entity}:{id}

# Cache with hash (partial updates):
HSET cache:{entity}:{id} {field} {value}
EXPIRE cache:{entity}:{id} {cache_ttl}
            ]]>
        </cache_pattern>

        <rate_limit_pattern>
            <![CDATA[
# Rate Limiting (Fixed Window)
# Key: rate:{action}:{identifier}:{window}
# Type: STRING (counter)
# TTL: window duration

# Check and increment:
INCR rate:{action}:{identifier}:{window}
EXPIRE rate:{action}:{identifier}:{window} {window_seconds}  # Only on first INCR

# Check limit:
GET rate:{action}:{identifier}:{window}

# Sliding Window (more accurate):
# Key: rate:{action}:{identifier}
# Type: SORTED SET
ZADD rate:{action}:{identifier} {timestamp} {request_id}
ZREMRANGEBYSCORE rate:{action}:{identifier} 0 {timestamp - window}
ZCARD rate:{action}:{identifier}
            ]]>
        </rate_limit_pattern>

        <leaderboard_pattern>
            <![CDATA[
# Leaderboard
# Key: leaderboard:{name}
# Type: SORTED SET

# Add/Update score:
ZADD leaderboard:{name} {score} {member_id}

# Increment score:
ZINCRBY leaderboard:{name} {increment} {member_id}

# Get rank (0-based, highest first):
ZREVRANK leaderboard:{name} {member_id}

# Get top N:
ZREVRANGE leaderboard:{name} 0 {n-1} WITHSCORES

# Get score:
ZSCORE leaderboard:{name} {member_id}
            ]]>
        </leaderboard_pattern>

        <pub_sub_pattern>
            <![CDATA[
# Pub/Sub Events
# Channel: events:{entity}:{action}
# Channel: events:{entity}:{id}:{action}

# Publish:
PUBLISH events:{entity}:created {json_payload}
PUBLISH events:{entity}:{id}:updated {json_payload}

# Subscribe:
SUBSCRIBE events:{entity}:created
PSUBSCRIBE events:{entity}:*
            ]]>
        </pub_sub_pattern>

        <distributed_lock_pattern>
            <![CDATA[
# Distributed Lock (Redlock pattern)
# Key: lock:{resource}:{id}
# Type: STRING
# Value: {unique_token}
# TTL: {lock_ttl} seconds

# Acquire lock:
SET lock:{resource}:{id} {token} NX EX {lock_ttl}

# Release lock (Lua script for atomicity):
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end

# Extend lock:
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
            ]]>
        </distributed_lock_pattern>
    </pattern_templates>

    <footer>
        <![CDATA[
# =============================================
# Schema documentation complete
# =============================================
#
# Notes:
# 1. All keys should follow the naming conventions above
# 2. Set appropriate TTLs for cache and session keys
# 3. Use MULTI/EXEC for atomic operations
# 4. Consider using Lua scripts for complex atomic operations
# 5. Monitor memory usage with INFO memory
# 6. Use SCAN instead of KEYS in production
# =============================================
        ]]>
    </footer>
</redis_templates>
"""