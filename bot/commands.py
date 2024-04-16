import json
import logging
from bot.db import (
    execute_db_query_async,
    get_user_data,
    set_user_data,
    is_user_exists,
    original_text_table,
    translation_table,
)
from bot.callbacks import send_text2vote
from bot.utils import send_message
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def start_command(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.full_name

    try:
        await is_user_exists(user_id, username)
        message = "Welcome to the Echopod Builder!\n\nTo get started, please send:\n\n1. /contribute\n2. /vote"
        await send_message(user_id, message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Start command processed"}),
        }
    except Exception as e:
        logger.error(f"Failed to process start command: {e}")
        error_message = "An error occurred while processing the start command. Please try again later."
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error processing start command"}),
        }


async def contribute_command(update, context):
    user_id = update.effective_user.id
    await set_user_data(user_id, "contribute_mode", "True")
    await set_user_data(user_id, "auto_contribute", "True")
    await set_user_data(user_id, "paused", "False")

    response = await execute_db_query_async(
        operation="scan",
        filter_expression="attribute_not_exists(translation_id)",
        limit=1,
        table=original_text_table,
    )

    if response["Count"] > 0:
        result = response["Items"][0]
        message = f"Please translate the following English sentence to Burmese:\n\n{result['text']}"
        await set_user_data(user_id, "contribute_text_id", result["text_id"])
    else:
        message = (
            "No untranslated sentences available at the moment. Please try again later."
        )

    keyboard = [[InlineKeyboardButton("Skip", callback_data="skip_contribute")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await send_message(user_id, message, reply_markup=reply_markup)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Contribute command processed"}),
        }
    except Exception as e:
        logger.error(f"Failed to send contribute message: {e}")
        error_message = "An error occurred while processing the contribute command. Please try again later."
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error processing contribute command"}),
        }


async def vote_command(update, context):
    user_id = update.effective_user.id
    try:
        await set_user_data(user_id, "auto_vote", "False")
        await set_user_data(user_id, "paused", "False")

        # Check if this is the first time the user is using the /vote command
        saw_best_practices = await get_user_data(user_id, "saw_best_practices")
        if not saw_best_practices:
            await set_user_data(user_id, "saw_best_practices", "True")

            voting_rules = (
                "ဘာသာပြန်ဆိုမှုတစ်ခုကို အမှတ်ပေးရန်၊ နံပါတ်တစ်ခုကို ရွေးချယ်ပါ။\n\n"
                "1 - အလွန်ညံ့သော/မှားသော\n"
                "2 - ညံ့သော\n"
                "3 - သာမန်\n"
                "4 - ကောင်းမွန်သော\n"
                "5 - အထူးကောင်းမွန်သော\n\n"
                "မဲစပေးရန် 'OK' ကို နှိပ်ပါ။"
            )
            keyboard = [[InlineKeyboardButton("OK", callback_data="start_voting")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await send_message(user_id, voting_rules, reply_markup=reply_markup)
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Vote command processed"}),
            }
        else:
            await send_text2vote(update, context)
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Vote command processed"}),
            }
    except Exception as e:
        logger.error(f"Error in vote_command: {e}")
        error_message = "An error occurred while processing the vote command. Please try again later."
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error processing vote command"}),
        }


async def leaderboard_command(update, context):
    try:
        response = await execute_db_query_async(
            operation="query",
            index_name="OriginalTextIndex",
            limit=10,
            table=translation_table,
        )

        if "Items" in response and response["Items"]:
            leaderboard_data = {}
            for item in response["Items"]:
                user_id = item["user_id"]
                if user_id in leaderboard_data:
                    leaderboard_data[user_id]["count"] += 1
                else:
                    user_response = await execute_db_query_async(
                        operation="get_item",
                        key_condition_expression={"user_id": user_id},
                        table=user_table,
                    )
                    if "Item" in user_response:
                        username = user_response["Item"]["username"]
                        leaderboard_data[user_id] = {"username": username, "count": 1}

            leaderboard_text = "Top 10 Contributors:\n\n"
            leaderboard_data = sorted(
                leaderboard_data.values(), key=lambda x: x["count"], reverse=True
            )
            for rank, data in enumerate(leaderboard_data, start=1):
                leaderboard_text += (
                    f"{rank}. {data['username']}: {data['count']} contributions\n"
                )
        else:
            leaderboard_text = "No contributions found."

        await send_message(update.effective_user.id, leaderboard_text)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Leaderboard command processed"}),
        }
    except Exception as e:
        logger.error(f"Error in leaderboard_command: {e}")
        error_message = "An error occurred while fetching the leaderboard."
        await send_message(update.effective_user.id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error processing leaderboard command"}),
        }


async def stop_command(update, context):
    user_id = update.effective_user.id
    await set_user_data(user_id, "auto_contribute", "False")
    await set_user_data(user_id, "auto_vote", "False")
    await set_user_data(user_id, "paused", "True")

    try:
        await send_message(user_id, "Please use /contribute or /vote to start again.")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Stop command processed"}),
        }
    except Exception as e:
        logger.error(f"Error in stop_command: {e}")
        error_message = "An error occurred while processing the stop command. Please try again later."
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error processing stop command"}),
        }
