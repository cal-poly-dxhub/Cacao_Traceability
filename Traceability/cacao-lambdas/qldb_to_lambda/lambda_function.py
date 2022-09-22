import os
import json
from dateutil import parser

# Parsing Kinesis Stream
from aws_kinesis_agg.deaggregator import deaggregate_records
from filtered_records_generator import filtered_records_generator

# Neptune
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection

endpoint = os.environ["NEPTUNE_ENDPOINT"]

g = traversal().withRemote(
    DriverRemoteConnection(f"wss://{endpoint}:8182/gremlin", "g")
)

def insertIntoNeptune(data):
    (
        g.V()
        .has("Bucket", "bucketId", data["source"]).as_("fromBucket").V()
        .has("Bucket", "bucketId", data["dest"]).as_("toBucket")
        .addE("DroppedInto")
        .from_("fromBucket")
        .to("toBucket")
        .property("transactionId", data["uuid"])
        .property("timestamp", parser.parse(data["time_stamp"]))
        .property("farmerId", data["farmerId"])
        .property("emptied", data["source_is_empty"] in ['true', 'True', 'TRUE', 1, 'Yes', 'yes', 'YES'])
        .next()
    )

def lambda_handler(event, context):
    raw_kinesis_records = event['Records']

    records = deaggregate_records(raw_kinesis_records)

    for record in filtered_records_generator(records, table_names=["transactions"]):
        print("found a record")
        print(record)
        insertIntoNeptune(record['revision_data'])

        

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
