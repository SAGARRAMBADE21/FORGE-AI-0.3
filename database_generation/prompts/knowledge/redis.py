REDIS_XML = """
<redis>
    <info>
        <name>Redis</name>
        <type>In-memory data structure store</type>
        <features>Caching, pub/sub, streams, Lua scripting, cluster mode</features>
        <use_cases>Session store, cache, message broker, leaderboards, rate limiting</use_cases>
    </info>

    <data_structures>
        <string>
            <description>Binary-safe strings up to 512MB</description>
            <commands>
                <cmd>SET key value [EX seconds] [NX|XX]</cmd>
                <cmd>GET key</cmd>
                <cmd>MSET key1 val1 key2 val2</cmd>
                <cmd>MGET key1 key2</cmd>
                <cmd>INCR key</cmd>
                <cmd>INCRBY key amount</cmd>
                <cmd>DECR key</cmd>
                <cmd>APPEND key value</cmd>
                <cmd>SETNX key value</cmd>
                <cmd>SETEX key seconds value</cmd>
            </commands>
            <use_cases>Caching, counters, rate limiting</use_cases>
        </string>

        <list>
            <description>Linked list of strings</description>
            <commands>
                <cmd>LPUSH key value [value...]</cmd>
                <cmd>RPUSH key value [value...]</cmd>
                <cmd>LPOP key [count]</cmd>
                <cmd>RPOP key [count]</cmd>
                <cmd>LRANGE key start stop</cmd>
                <cmd>LLEN key</cmd>
                <cmd>LINDEX key index</cmd>
                <cmd>LSET key index value</cmd>
                <cmd>LREM key count value</cmd>
                <cmd>BLPOP key [key...] timeout</cmd>
                <cmd>BRPOP key [key...] timeout</cmd>
            </commands>
            <use_cases>Queues, recent items, activity feeds</use_cases>
        </list>

        <set>
            <description>Unordered collection of unique strings</description>
            <commands>
                <cmd>SADD key member [member...]</cmd>
                <cmd>SREM key member [member...]</cmd>
                <cmd>SMEMBERS key</cmd>
                <cmd>SISMEMBER key member</cmd>
                <cmd>SCARD key</cmd>
                <cmd>SINTER key [key...]</cmd>
                <cmd>SUNION key [key...]</cmd>
                <cmd>SDIFF key [key...]</cmd>
                <cmd>SRANDMEMBER key [count]</cmd>
            </commands>
            <use_cases>Tags, unique visitors, social connections</use_cases>
        </set>

        <sorted_set>
            <description>Set with score for ordering</description>
            <commands>
                <cmd>ZADD key score member [score member...]</cmd>
                <cmd>ZREM key member [member...]</cmd>
                <cmd>ZSCORE key member</cmd>
                <cmd>ZRANK key member</cmd>
                <cmd>ZREVRANK key member</cmd>
                <cmd>ZRANGE key start stop [WITHSCORES]</cmd>
                <cmd>ZREVRANGE key start stop [WITHSCORES]</cmd>
                <cmd>ZRANGEBYSCORE key min max</cmd>
                <cmd>ZCOUNT key min max</cmd>
                <cmd>ZINCRBY key increment member</cmd>
                <cmd>ZCARD key</cmd>
            </commands>
            <use_cases>Leaderboards, priority queues, time-series, secondary indexes</use_cases>
        </sorted_set>

        <hash>
            <description>Map of field-value pairs</description>
            <commands>
                <cmd>HSET key field value [field value...]</cmd>
                <cmd>HGET key field</cmd>
                <cmd>HMGET key field [field...]</cmd>
                <cmd>HGETALL key</cmd>
                <cmd>HDEL key field [field...]</cmd>
                <cmd>HEXISTS key field</cmd>
                <cmd>HKEYS key</cmd>
                <cmd>HVALS key</cmd>
                <cmd>HLEN key</cmd>
                <cmd>HINCRBY key field increment</cmd>
            </commands>
            <use_cases>Object storage, user profiles, counters per object</use_cases>
        </hash>

        <stream>
            <description>Append-only log with consumer groups</description>
            <commands>
                <cmd>XADD key * field value [field value...]</cmd>
                <cmd>XREAD COUNT n STREAMS key id</cmd>
                <cmd>XRANGE key start end [COUNT n]</cmd>
                <cmd>XLEN key</cmd>
                <cmd>XGROUP CREATE key group id</cmd>
                <cmd>XREADGROUP GROUP group consumer STREAMS key id</cmd>
                <cmd>XACK key group id [id...]</cmd>
            </commands>
            <use_cases>Event sourcing, message queues, activity streams</use_cases>
        </stream>

        <hyperloglog>
            <description>Probabilistic cardinality estimation</description>
            <commands>
                <cmd>PFADD key element [element...]</cmd>
                <cmd>PFCOUNT key [key...]</cmd>
                <cmd>PFMERGE destkey sourcekey [sourcekey...]</cmd>
            </commands>
            <use_cases>Unique visitor counting, distinct counts</use_cases>
        </hyperloglog>

        <bitmap>
            <description>Bit array operations</description>
            <commands>
                <cmd>SETBIT key offset value</cmd>
                <cmd>GETBIT key offset</cmd>
                <cmd>BITCOUNT key [start end]</cmd>
                <cmd>BITOP operation destkey key [key...]</cmd>
            </commands>
            <use_cases>Feature flags, user activity tracking, bloom filters</use_cases>
        </bitmap>

        <geospatial>
            <description>Geographic coordinates storage and queries</description>
            <commands>
                <cmd>GEOADD key longitude latitude member</cmd>
                <cmd>GEOPOS key member [member...]</cmd>
                <cmd>GEODIST key member1 member2 [unit]</cmd>
                <cmd>GEOSEARCH key FROMMEMBER member BYRADIUS radius unit</cmd>
                <cmd>GEORADIUS key longitude latitude radius unit</cmd>
            </commands>
            <use_cases>Location-based services, nearby search</use_cases>
        </geospatial>
    </data_structures>

    <key_patterns>
        <pattern name="namespace">
            <format>namespace:entity:id</format>
            <examples>
                <example>user:123</example>
                <example>user:123:profile</example>
                <example>user:123:sessions</example>
                <example>order:456</example>
                <example>cache:products:789</example>
            </examples>
        </pattern>
        <pattern name="secondary_index">
            <description>Use sorted sets for secondary indexes</description>
            <example>
ZADD users:by_email 0 "user:123"
HSET user:123 email "a@b.com" name "Alice"
            </example>
        </pattern>
    </key_patterns>

    <expiration>
        <commands>
            <cmd>EXPIRE key seconds</cmd>
            <cmd>EXPIREAT key timestamp</cmd>
            <cmd>PEXPIRE key milliseconds</cmd>
            <cmd>TTL key</cmd>
            <cmd>PTTL key</cmd>
            <cmd>PERSIST key</cmd>
        </commands>
        <patterns>
            <session>SET session:token data EX 3600</session>
            <cache>SETEX cache:key 300 data</cache>
        </patterns>
    </expiration>

    <transactions>
        <multi_exec>
            <syntax>
MULTI
SET key1 value1
SET key2 value2
EXEC
            </syntax>
        </multi_exec>
        <watch>
            <description>Optimistic locking</description>
            <syntax>
WATCH key
val = GET key
MULTI
SET key newval
EXEC
            </syntax>
        </watch>
        <lua_scripts>
            <description>Atomic operations with Lua</description>
            <syntax>
EVAL "return redis.call('GET', KEYS[1])" 1 mykey
            </syntax>
        </lua_scripts>
    </transactions>

    <pub_sub>
        <commands>
            <cmd>SUBSCRIBE channel [channel...]</cmd>
            <cmd>PUBLISH channel message</cmd>
            <cmd>UNSUBSCRIBE channel [channel...]</cmd>
            <cmd>PSUBSCRIBE pattern [pattern...]</cmd>
        </commands>
        <use_cases>Real-time notifications, chat, event broadcasting</use_cases>
    </pub_sub>

    <persistence>
        <rdb>
            <description>Point-in-time snapshots</description>
            <config>save 900 1 (save after 900s if 1 key changed)</config>
        </rdb>
        <aof>
            <description>Append-only file logging</description>
            <config>appendonly yes</config>
            <policies>always, everysec, no</policies>
        </aof>
    </persistence>

    <cluster>
        <description>Horizontal scaling with automatic sharding</description>
        <hash_slots>16384 slots distributed across nodes</hash_slots>
        <commands>
            <cmd>CLUSTER NODES</cmd>
            <cmd>CLUSTER INFO</cmd>
            <cmd>CLUSTER SLOTS</cmd>
        </commands>
    </cluster>

    <common_patterns>
        <caching>
            <read_through>
GET cache:key
if miss: fetch from DB, SET cache:key value EX ttl
            </read_through>
            <write_through>
SET cache:key value
write to DB
            </write_through>
            <invalidation>DEL cache:key (on update)</invalidation>
        </caching>

        <session_store>
            <set>SETEX session:token 3600 user_data</set>
            <get>GET session:token</get>
            <refresh>EXPIRE session:token 3600</refresh>
            <delete>DEL session:token</delete>
        </session_store>

        <rate_limiting>
            <fixed_window>
INCR rate:user:123:minute
EXPIRE rate:user:123:minute 60
            </fixed_window>
            <sliding_window>
ZADD rate:user:123 timestamp request_id
ZREMRANGEBYSCORE rate:user:123 0 (now - window)
ZCARD rate:user:123
            </sliding_window>
        </rate_limiting>

        <leaderboard>
            <add_score>ZINCRBY leaderboard:game score user_id</add_score>
            <get_rank>ZREVRANK leaderboard:game user_id</get_rank>
            <top_10>ZREVRANGE leaderboard:game 0 9 WITHSCORES</top_10>
        </leaderboard>

        <distributed_lock>
            <acquire>SET lock:resource token NX EX 30</acquire>
            <release>
if GET lock:resource == token:
    DEL lock:resource
            </release>
            <redlock>Use Redlock algorithm for distributed locks</redlock>
        </distributed_lock>
    </common_patterns>

    <modules>
        <module name="RedisJSON">JSON document storage with path operations</module>
        <module name="RediSearch">Full-text search and secondary indexing</module>
        <module name="RedisGraph">Graph database on Redis</module>
        <module name="RedisTimeSeries">Time-series data handling</module>
        <module name="RedisBloom">Probabilistic data structures</module>
    </modules>
</redis>
"""
