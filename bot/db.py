import boto3
import logging
import random
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from config import DYNAMODB_TABLE_PREFIX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
user_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_User")
original_text_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_OriginalText")
translation_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_Translation")
score_table = dynamodb.Table(f"{DYNAMODB_TABLE_PREFIX}_Score")


def execute_db_query(operation, **kwargs):
    table = kwargs.pop("table")
    try:
        if operation == "get_item":
            return table.get_item(**kwargs)
        elif operation == "put_item":
            return table.put_item(**kwargs)
        elif operation == "update_item":
            return table.update_item(**kwargs)
        elif operation == "query":
            return table.query(**kwargs)
        elif operation == "scan":
            return table.scan(**kwargs)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    except ClientError as e:
        logger.exception(f"Failed to execute {operation}")
        raise e


def get_user_data(user_id, key):
    try:
        response = execute_db_query(
            operation="get_item",
            Key={"user_id": str(user_id)},
            table=user_table,
        )
        return response.get("Item", {}).get(key)
    except ClientError as e:
        logger.exception("Failed to get user data")
        raise e


def set_user_data(user_id, key, value):
    try:
        execute_db_query(
            operation="update_item",
            Key={"user_id": str(user_id)},
            UpdateExpression=f"SET {key} = :value",
            ExpressionAttributeValues={":value": value},
            table=user_table,
        )
    except ClientError as e:
        logger.exception("Failed to set user data")
        raise e


def is_user_exists(user_id, username):
    try:
        response = execute_db_query(
            operation="get_item",
            Key={"user_id": str(user_id)},
            table=user_table,
        )
        if "Item" not in response:
            add_new_user(user_id, username)
    except ClientError as e:
        logger.exception("Failed to check user existence")
        raise e


def add_new_user(user_id, username):
    try:
        execute_db_query(
            operation="put_item",
            Item={
                "user_id": str(user_id),
                "username": username,
            },
            table=user_table,
        )
    except ClientError as e:
        logger.exception("Failed to add new user")
        raise e


def get_user_details(user_id):
    try:
        response = execute_db_query(
            operation="get_item",
            Key={"user_id": str(user_id)},
            table=user_table,
        )
        return response.get("Item")
    except ClientError as e:
        logger.exception("Failed to get user details")
        raise e


def get_original_text_by_id(text_id):
    try:
        response = execute_db_query(
            operation="get_item",
            Key={"text_id": int(text_id)},
            table=original_text_table,
        )
        return response.get("Item")
    except ClientError as e:
        logger.exception("Failed to get original text by ID")
        raise e


def get_translation_by_id(translation_id):
    try:
        response = execute_db_query(
            operation="get_item",
            Key={"translation_id": int(translation_id)},
            table=translation_table,
        )
        return response.get("Item")
    except ClientError as e:
        logger.exception("Failed to get translation by ID")
        raise e


def get_untranslated_text():
    try:
        while True:
            # Generate a random number between 0 and a large value (e.g., 400000)
            random_index = random.randint(0, 400000)

            # Query the original_text_table using the translated-index to get a random untranslated text
            response = execute_db_query(
                operation="query",
                table=original_text_table,
                IndexName="translated-text_id-index",
                KeyConditionExpression=Key("translated").eq("False"),
                Limit=1,
                ExclusiveStartKey={"translated": "False", "text_id": random_index},
            )

            if response["Items"]:
                return response["Items"][0]
            else:
                # If no matching item is found, retry with a new random number
                continue
    except ClientError as e:
        logger.exception("Failed to get untranslated text")
        raise e


def get_unvoted_translation():
    try:
        while True:
            # Generate a random number between 0 and a large value (e.g., 1000000)
            random_index = random.randint(0, 1000000)

            # Query the translation_table using the voted-index to get a random unvoted translation
            response = execute_db_query(
                operation="query",
                table=translation_table,
                IndexName="voted-translation_id-index",
                KeyConditionExpression=Key("voted").eq("False"),
                Limit=1,
                ExclusiveStartKey={"voted": "False", "translation_id": random_index},
            )

            if response["Items"]:
                return response["Items"][0] if response["Items"] else None
            else:
                continue
    except ClientError as e:
        logger.exception("Failed to get unvoted translation")
        raise e


def get_original_text(text_id):
    try:
        response = execute_db_query(
            operation="get_item",
            Key={"text_id": int(text_id)},
            table=original_text_table,
        )
        item = response.get("Item")
        if item:
            return item["text"]
        else:
            return None
    except ClientError as e:
        logger.exception("Failed to get original text")
        raise e


def save_contribution(text_id, user_id, lang, text, original_text):
    try:
        execute_db_query(
            operation="put_item",
            Item={
                "translation_id": int(f"{text_id}{user_id}"),
                "voted": "False",
                "lang": lang,
                "original_text": original_text,
                "original_text_id": str(text_id),
                "text": text,
                "user_id": str(user_id),
            },
            ConditionExpression="attribute_not_exists(translation_id)",
            table=translation_table,
        )
        execute_db_query(
            operation="update_item",
            Key={"text_id": int(text_id)},
            UpdateExpression="SET translated = :translated",
            ExpressionAttributeValues={":translated": "True"},
            table=original_text_table,
        )
        execute_db_query(
            operation="update_item",
            Key={"user_id": str(user_id)},
            UpdateExpression="SET contributions = if_not_exists(contributions, :zero) + :inc",
            ExpressionAttributeValues={":zero": 0, ":inc": 1},
            table=user_table,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(f"Contribution already exists for text_id: {text_id}")
        else:
            logger.exception("Failed to save contribution")
        raise e


def save_vote(translation_id, user_id, score):
    try:
        execute_db_query(
            operation="put_item",
            Item={
                "score_id": int(f"{translation_id}{user_id}"),
                "score_value": int(score),
                "translation_id": str(translation_id),
                "user_id": str(user_id),
            },
            ConditionExpression="attribute_not_exists(score_id)",
            table=score_table,
        )

        execute_db_query(
            operation="update_item",
            Key={"translation_id": int(translation_id)},
            UpdateExpression="SET voted = :voted",
            ExpressionAttributeValues={":voted": "True"},
            table=translation_table,
        )

        execute_db_query(
            operation="update_item",
            table=user_table,
            Key={"user_id": str(user_id)},
            UpdateExpression="SET votings = if_not_exists(votings, :zero) + :inc",
            ExpressionAttributeValues={":zero": 0, ":inc": 1},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(
                f"Vote already exists for translation_id: {translation_id} and user_id: {user_id}"
            )
        else:
            logger.exception("Failed to save vote")
        raise e


def get_leaderboard_data():
    try:
        response = execute_db_query(
            operation="scan",
            table=user_table,
        )
        leaderboard_data = []
        for item in response.get("Items", []):
            user_id = item["user_id"]
            if user_id == "1":  # Skip the bot's user ID
                continue
            username = item.get(
                "username", "Unknown"
            )  # for some reasons username could be empty
            contributions = float(item.get("contributions", 0))
            votings = float(item.get("votings", 0))
            score = round(contributions + (votings / 10))
            leaderboard_data.append(
                {
                    "user_id": user_id,
                    "username": username,
                    "score": score,
                }
            )

        return sorted(leaderboard_data, key=lambda x: x["score"], reverse=True)[:10]
    except ClientError as e:
        logger.exception("Failed to get leaderboard data")
        raise e


def get_total_users():
    try:
        response = execute_db_query(
            operation="scan",
            table=user_table,
            Select="COUNT",
        )
        return response["Count"]
    except ClientError as e:
        logger.exception("Failed to get total users")
        raise e


def get_total_contributions():
    try:
        response = execute_db_query(
            operation="scan",
            table=user_table,
            FilterExpression=Attr("user_id").ne("1"),  # Exclude the bot's user ID
            ProjectionExpression="contributions",
        )
        total_contributions = sum(
            int(item.get("contributions", 0)) for item in response.get("Items", [])
        )
        return total_contributions
    except ClientError as e:
        logger.exception("Failed to get total contributions")
        raise e


def get_total_votings():
    try:
        response = execute_db_query(
            operation="scan",
            table=score_table,
            Select="COUNT",
        )
        return response["Count"]
    except ClientError as e:
        logger.exception("Failed to get total votings")
        raise e
