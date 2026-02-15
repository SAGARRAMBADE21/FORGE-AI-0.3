"""MongoDB-specific knowledge base."""
MONGODB_XML = """
<mongodb>
    <info>
        <name>MongoDB</name>
        <type>NoSQL document database</type>
        <features>Flexible schema, horizontal scaling, aggregation pipeline, change streams</features>
    </info>

    <document_design>
        <embed when="true">
            <criterion>Data accessed together</criterion>
            <criterion>Data is small/bounded</criterion>
            <criterion>Rarely updated</criterion>
            <criterion>1:1 or 1:few relationship</criterion>
        </embed>
        <reference when="true">
            <criterion>Data accessed separately</criterion>
            <criterion>Data is large/unbounded</criterion>
            <criterion>Frequently updated</criterion>
            <criterion>1:many or many:many</criterion>
        </reference>
    </document_design>

    <schema_validation>
        <syntax>
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["email", "created_at"],
      properties: {
        _id: { bsonType: "objectId" },
        email: { bsonType: "string", pattern: "^.+@.+$" },
        name: { bsonType: "string", maxLength: 100 },
        age: { bsonType: "int", minimum: 0, maximum: 150 },
        role: { enum: ["admin", "user", "guest"] },
        tags: { bsonType: "array", items: { bsonType: "string" } },
        created_at: { bsonType: "date" }
      }
    }
  },
  validationLevel: "moderate",
  validationAction: "error"
});
        </syntax>
    </schema_validation>

    <indexes>
        <single>db.users.createIndex({ email: 1 })</single>
        <compound>db.orders.createIndex({ user_id: 1, created_at: -1 })</compound>
        <unique>db.users.createIndex({ email: 1 }, { unique: true })</unique>
        <partial>db.users.createIndex({ email: 1 }, { partialFilterExpression: { status: "active" } })</partial>
        <sparse>db.users.createIndex({ phone: 1 }, { sparse: true })</sparse>
        <ttl>db.sessions.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 })</ttl>
        <text>db.articles.createIndex({ title: "text", content: "text" })</text>
        <geospatial>db.places.createIndex({ location: "2dsphere" })</geospatial>
        <hashed>db.users.createIndex({ user_id: "hashed" })</hashed>
        <wildcard>db.products.createIndex({ "attributes.$**": 1 })</wildcard>
    </indexes>

    <aggregation>
        <stages>
            <stage name="$match">Filter documents</stage>
            <stage name="$project">Shape output</stage>
            <stage name="$group">Group and aggregate</stage>
            <stage name="$sort">Sort results</stage>
            <stage name="$limit">Limit results</stage>
            <stage name="$skip">Skip results</stage>
            <stage name="$lookup">Join collections</stage>
            <stage name="$unwind">Flatten arrays</stage>
            <stage name="$addFields">Add computed fields</stage>
            <stage name="$facet">Multiple pipelines</stage>
        </stages>
        <example>
db.orders.aggregate([
  { $match: { status: "completed" } },
  { $lookup: { from: "users", localField: "user_id", foreignField: "_id", as: "user" } },
  { $unwind: "$user" },
  { $group: { _id: "$user._id", total: { $sum: "$amount" }, count: { $sum: 1 } } },
  { $sort: { total: -1 } },
  { $limit: 10 }
]);
        </example>
    </aggregation>

    <transactions>
        <syntax>
const session = client.startSession();
try {
  session.startTransaction();
  await db.accounts.updateOne({ _id: from }, { $inc: { balance: -amount } }, { session });
  await db.accounts.updateOne({ _id: to }, { $inc: { balance: amount } }, { session });
  await session.commitTransaction();
} catch (e) {
  await session.abortTransaction();
} finally {
  session.endSession();
}
        </syntax>
    </transactions>

    <sharding>
        <enable>sh.enableSharding("mydb")</enable>
        <shard_collection>sh.shardCollection("mydb.orders", { user_id: "hashed" })</shard_collection>
        <compound_key>sh.shardCollection("mydb.events", { tenant_id: 1, created_at: 1 })</compound_key>
    </sharding>

    <patterns>
        <bucket desc="Time-series">
            <document>{ sensor_id: "s1", date: ISODate(), readings: [...], count: 100, sum: 2350 }</document>
        </bucket>
        <computed desc="Denormalized aggregates">
            <document>{ title: "Product", reviews: [...], review_count: 150, avg_rating: 4.5 }</document>
        </computed>
        <polymorphic desc="Multiple types in one collection">
            <document>{ type: "product", name: "Laptop", specs: {...} }</document>
            <document>{ type: "service", name: "Consulting", hourly_rate: 150 }</document>
        </polymorphic>
    </patterns>
</mongodb>
"""
