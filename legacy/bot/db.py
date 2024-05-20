import boto3
import logging
from botocore.exceptions import ClientError
from bot.config import DYNAMODB_TABLE_PREFIX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
user_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_User")
user_data_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_UserData")
original_text_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_OriginalText")
translation_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_Translation")
score_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_Score")


async def execute_db_query_async(
    operation,
    key_condition_expression=None,
    filter_expression=None,
    expression_attribute_values=None,
    index_name=None,
    limit=None,
    table=None,
):
    try:
        if operation == "get_item":
            response = table.get_item(Key=key_condition_expression)
        elif operation == "put_item":
            response = table.put_item(Item=expression_attribute_values)
        elif operation == "update_item":
            response = table.update_item(
                Key=key_condition_expression,
                UpdateExpression=expression_attribute_values["UpdateExpression"],
                ExpressionAttributeValues=expression_attribute_values[
                    "ExpressionAttributeValues"
                ],
            )
        elif operation == "query":
            if index_name:
                response = table.query(
                    IndexName=index_name,
                    KeyConditionExpression=key_condition_expression,
                    FilterExpression=filter_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    Limit=limit,
                )
            else:
                response = table.query(
                    KeyConditionExpression=key_condition_expression,
                    FilterExpression=filter_expression,
                    ExpressionAttributeValues=expression_attribute_values,
                    Limit=limit,
                )
        elif operation == "scan":
            response = table.scan(
                FilterExpression=filter_expression,
                ExpressionAttributeValues=expression_attribute_values,
                Limit=limit,
            )
    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        raise

    return response


async def get_user_data(user_id, key):
    try:
        response = await execute_db_query_async(
            operation="get_item",
            table=user_data_table,
            key_condition_expression={"user_id": str(user_id)},
        )
        if "Item" in response:
            return response["Item"].get(key)
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting user data for user {user_id} and key {key}: {e}")
        return None


async def set_user_data(user_id, key, value):
    try:
        await execute_db_query_async(
            operation="update_item",
            table=user_data_table,
            key_condition_expression={"user_id": str(user_id)},
            expression_attribute_values={
                "UpdateExpression": f"SET {key} = :value",
                "ExpressionAttributeValues": {":value": value},
            },
        )
    except Exception as e:
        logger.error(
            f"Error setting user data for user {user_id}, key {key}, and value {value}: {e}"
        )


async def is_user_exists(user_id, username):
    response = await execute_db_query_async(
        operation="get_item",
        key_condition_expression={"user_id": str(user_id)},
        table=user_table,
    )
    if "Item" not in response:
        await add_new_user(user_id, username)


async def add_new_user(user_id, username):
    await execute_db_query_async(
        operation="put_item",
        table=user_table,
        expression_attribute_values={
            "user_id": str(user_id),
            "username": username,
        },
    )


async def get_user_details(user_id):
    response = await execute_db_query_async(
        operation="get_item",
        key_condition_expression={"user_id": str(user_id)},
        table=user_table,
    )
    return response.get("Item")


async def get_untranslated_text():
    response = await execute_db_query_async(
        operation="scan",
        filter_expression="attribute_not_exists(translation_id)",
        limit=1,
        table=original_text_table,
    )
    return response["Items"][0] if response["Count"] > 0 else None


async def get_translation_by_id(translation_id):
    response = await execute_db_query_async(
        operation="get_item",
        key={"id": str(translation_id)},
        table=translation_table,
    )
    return response.get("Item")


async def get_unvoted_translation():
    response = await execute_db_query_async(
        operation="scan",
        filter_expression="attribute_not_exists(score)",
        limit=1,
        table=translation_table,
    )
    return response["Items"][0] if response["Count"] > 0 else None


async def get_original_text(original_text_id):
    response = await execute_db_query_async(
        operation="get_item",
        key={"text_id": str(original_text_id)},
        table=original_text_table,
    )
    return response["Item"]["text"]


async def get_leaderboard_data():
    response = await execute_db_query_async(
        operation="query",
        index_name="OriginalTextIndex",
        limit=10,
        table=translation_table,
    )
    return response.get("Items", [])
