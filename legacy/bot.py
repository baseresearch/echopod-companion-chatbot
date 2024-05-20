import os
import logging
import boto3
import json
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from dotenv import load_dotenv
from bot.config import VOTING_SESSION_THRESHOLD

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DYNAMODB_TABLE_PREFIX = os.getenv("DYNAMODB_TABLE_PREFIX")

dynamodb = boto3.resource("dynamodb")
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
            key={"user_id": user_id},
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
            key={"user_id": user_id},
            update_expression=f"SET {key} = :value",
            expression_attribute_values={":value": value},
        )
    except Exception as e:
        logger.error(
            f"Error setting user data for user {user_id}, key {key}, and value {value}: {e}"
        )


async def is_user_exists(user_id, username):
    response = await execute_db_query_async(
        operation="get_item",
        key_condition_expression={"user_id": user_id},
        table=user_table,
    )
    if "Item" not in response:
        await add_new_user(user_id, username)


async def add_new_user(user_id, username):
    await execute_db_query_async(
        operation="put_item",
        expression_attribute_values={"user_id": user_id, "username": username},
        table=user_table,
    )


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


async def send_text2vote(update, context):
    user_id = update.effective_user.id
    translation_id = await get_user_data(user_id, "translation_id")
    if translation_id:
        response = await execute_db_query_async(
            operation="query",
            key_condition_expression={"translation_id": translation_id},
            limit=1,
            table=translation_table,
        )
        if response["Count"] > 0:
            result = response["Items"][0]
            original_text_response = await execute_db_query_async(
                operation="get_item",
                key_condition_expression={"text_id": result["original_text_id"]},
                table=original_text_table,
            )
            original_text = original_text_response["Item"]["text"]
            message = (
                f"🐬\n"
                + "အောက်ပါဘာသာပြန်ဆိုမှုအား 1 မှ 5 အတွင်း အဆင့်သတ်မှတ်ပေးပါ:\n\n"
                + "English:\n----------| "
                + f"{original_text}\n\n"
                + "Burmese:\n----------| "
                + f"{result['text']}\n"
            )
    else:
        message = "No translations available for scoring at the moment. Please try again later."

    keyboard = [
        [
            InlineKeyboardButton(
                str(score), callback_data=f"vote_{result['translation_id']}_{score}"
            )
            for score in range(1, 6)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await send_message(user_id, message, reply_markup=reply_markup)
        return {"statusCode": 200, "body": json.dumps({"message": "Text to vote sent"})}
    except Exception as e:
        logger.error(f"Error sending text to vote: {e}")
        error_message = (
            "An error occurred while sending the text to vote. Please try again later."
        )
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error sending text to vote"}),
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


async def handle_text(update, context):
    user_id = update.effective_user.id
    interaction_interval = await calculate_interaction_interval(user_id)
    await update_avg_interaction_interval(user_id, interaction_interval)
    await set_user_data(user_id, "last_interaction_time", str(datetime.now()))

    # Check if the user is in contribution mode
    contribute_mode = await get_user_data(user_id, "contribute_mode")
    if contribute_mode:
        # Handle the contribution
        await handle_contribution(update, context)
    else:
        message = "Please use the provided commands to interact with the bot."
        await send_message(user_id, message)

    return {"statusCode": 200, "body": json.dumps({"message": "Text handled"})}


async def handle_contribution(update, context):
    user_id = update.effective_user.id
    contribution_interval = await calculate_interaction_interval(user_id)
    await update_avg_interaction_interval(user_id, contribution_interval)
    await set_user_data(user_id, "last_interaction_time", datetime.now())

    text_id = await get_user_data(user_id, "contribute_text_id")
    translated_text = update.message.text

    if not text_id:
        message = "No contribution context found. Please use the /contribute command to start contributing."
        await send_message(user_id, message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Contribution handled"}),
        }

    try:
        await execute_db_query_async(
            operation="put_item",
            expression_attribute_values={
                "original_text_id": text_id,
                "user_id": user_id,
                "lang": "my",
                "text": translated_text,
            },
            table=translation_table,
        )
        message = "Thank you for your contribution!"
    except Exception as e:
        message = f"Failed to save your contribution due to an error: {e}"

    # Reset the contribution mode
    await set_user_data(user_id, "contribute_mode", "False")

    # Send the message to the user
    await send_message(user_id, message)

    # Check if auto_contribute mode is enabled, then automatically fetch the next item for contribution
    auto_contribute = await get_user_data(user_id, "auto_contribute")
    if auto_contribute:
        await contribute_command(update, context)

    return {"statusCode": 200, "body": json.dumps({"message": "Contribution handled"})}


async def handle_skip_contribution(update, context):
    user_id = update.effective_user.id
    interaction_interval = await calculate_interaction_interval(user_id)
    await update_avg_interaction_interval(user_id, interaction_interval)
    await set_user_data(user_id, "last_interaction_time", str(datetime.now()))

    query = update.callback_query  # handle "Skip" contribution callback
    await query.answer()

    if query.data == "skip_contribute":
        await contribute_command(update, context)


async def handle_start_voting(update, context):
    user_id = update.effective_user.id
    try:
        voting_interval = await calculate_interaction_interval(user_id)
        await update_avg_interaction_interval(user_id, voting_interval)
        await set_user_data(user_id, "last_interaction_time", str(datetime.now()))

        query = update.callback_query
        await query.answer()

        if query.data == "start_voting":
            await edit_message_reply_markup(
                update.effective_chat.id,
                query.message.message_id,
                None,
            )
            await send_text2vote(update, context)
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Start voting handled"}),
            }
    except Exception as e:
        logger.error(f"Error in handle_start_voting: {e}")
        error_message = "An error occurred while starting the voting process. Please try again later."
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error handling start voting"}),
        }


async def handle_vote(update, context):
    user_id = update.effective_user.id
    try:
        voting_interval = await calculate_interaction_interval(user_id)
        await update_avg_interaction_interval(user_id, voting_interval)
        await set_user_data(user_id, "last_interaction_time", str(datetime.now()))

        query = update.callback_query  # handle user voting callback
        await query.answer()

        logger.info(f"Received vote callback: {query.data}")

        translation_id, score = query.data.split("_")[1:]
        await execute_db_query_async(
            operation="put_item",
            expression_attribute_values={
                "translation_id": translation_id,
                "user_id": user_id,
                "score": int(score),
            },
            table=score_table,
        )

        await edit_message_reply_markup(
            update.effective_chat.id,
            query.message.message_id,
            None,
        )

        # Check if auto_vote mode is enabled, then automatically fetch the next item for voting
        auto_vote = await get_user_data(user_id, "auto_vote")
        if auto_vote:
            await send_text2vote(update, context)

        return {"statusCode": 200, "body": json.dumps({"message": "Vote handled"})}
    except Exception as e:
        logger.error(f"Error in handle_vote: {e}")
        error_message = (
            "An error occurred while processing your vote. Please try again later."
        )
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error handling vote"}),
        }


async def reminder_job(event, context):
    response = await execute_db_query_async(
        operation="scan",
        table=user_data_table,
    )

    for item in response["Items"]:
        user_id = item["user_id"]
        paused = await get_user_data(user_id, "paused")
        if not paused:
            current_time = datetime.now()

            # Check reminder
            last_interaction_session_time = await get_user_data(
                user_id, "last_interaction_session_time"
            )
            avg_voting_interval = await get_user_data(user_id, "avg_voting_interval")
            if not avg_voting_interval:
                avg_voting_interval = timedelta(
                    hours=24
                ).total_seconds()  # Default to 24 hours

            if last_interaction_session_time and current_time - datetime.fromisoformat(
                last_interaction_session_time
            ) > timedelta(seconds=avg_voting_interval):
                await send_reminder_message(user_id)


async def send_reminder_message(user_id):
    message = "Hi! It's been a while since your last voting session.\n\nYour votes help ensure the quality of the 🐬 Echopod dataset.\n\nTake a moment to review some translations today! 🙏🐬"
    await send_message(user_id, message)


async def send_message(user_id, message, reply_markup=None):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending message to user {user_id}: {e}")


async def edit_message_reply_markup(chat_id, message_id, reply_markup):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=message_id, reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message reply markup: {e}")


async def calculate_interaction_interval(user_id):
    current_time = datetime.now()
    last_interaction_time = await get_user_data(user_id, "last_interaction_time")
    last_interaction_session_time = await get_user_data(
        user_id, "last_interaction_session_time"
    )

    if last_interaction_time:
        last_interaction_time = datetime.fromisoformat(last_interaction_time)
        if current_time - last_interaction_time <= VOTING_SESSION_THRESHOLD:
            await set_user_data(
                user_id, "last_interaction_session_time", str(current_time)
            )
            return None
        else:
            voting_interval = (
                current_time - datetime.fromisoformat(last_interaction_session_time)
            ).total_seconds()
            await set_user_data(
                user_id, "last_interaction_session_time", str(current_time)
            )
            return voting_interval
    else:
        await set_user_data(user_id, "last_interaction_session_time", str(current_time))
        return None


async def update_avg_interaction_interval(user_id, interval):
    avg_interval = await get_user_data(user_id, "avg_interaction_interval")
    if avg_interval:
        avg_interval = (float(avg_interval) + interval) / 2
    else:
        avg_interval = interval
    await set_user_data(user_id, "avg_interaction_interval", str(avg_interval))


def main():
    # Create an Application instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Check every hour for the reminder
    application.job_queue.run_repeating(reminder_job, interval=60 * 60, first=0)

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("contribute", contribute_command))
    application.add_handler(CommandHandler("vote", vote_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(
        CallbackQueryHandler(handle_start_voting, pattern="^start_voting$")
    )
    application.add_handler(CallbackQueryHandler(handle_vote, pattern="^vote_"))
    application.add_handler(
        CallbackQueryHandler(handle_skip_contribution, pattern="^skip_contribute$")
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contribution)
    )

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
