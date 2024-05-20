import json
import logging
from bot.db import (
    get_user_data,
    set_user_data,
    is_user_exists,
    get_user_details,
    get_untranslated_text,
    get_unvoted_translation,
    get_translation_by_id,
    get_original_text,
    get_leaderboard_data,
)
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

    result = await get_untranslated_text()

    if result:
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


async def simple_vote_command(update, context):
    user_id = update.effective_user.id
    await set_user_data(user_id, "vote_mode", "True")
    await set_user_data(user_id, "auto_vote", "True")
    await set_user_data(user_id, "paused", "False")

    result = await get_unvoted_translation()

    if result:
        original_text_id = result["original_text_id"]
        original_text = await get_original_text(original_text_id)
        translation = result["translation"]
        message = f"Please vote on the following translation:\n\nEnglish: {original_text}\nBurmese: {translation}"
        await set_user_data(user_id, "vote_translation_id", result["id"])
    else:
        message = "No translations available for voting at the moment. Please try again later."

    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data="upvote"),
            InlineKeyboardButton("👎", callback_data="downvote"),
        ],
        [InlineKeyboardButton("Skip", callback_data="skip_vote")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await send_message(user_id, message, reply_markup=reply_markup)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Vote command processed"}),
        }
    except Exception as e:
        logger.error(f"Failed to send vote message: {e}")
        error_message = "An error occurred while processing the vote command. Please try again later."
        await send_message(user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error processing vote command"}),
        }


async def leaderboard_command(update, context):
    leaderboard_data = await get_leaderboard_data()

    if leaderboard_data:
        message = "Top 10 Contributors:\n\n"
        for i, item in enumerate(leaderboard_data, start=1):
            user_details = await get_user_details(item["user_id"])
            username = user_details["username"] if user_details else "Unknown"
            message += f"{i}. {username} - {item['score']} points\n"
    else:
        message = "No leaderboard data available at the moment."

    try:
        await send_message(update.effective_user.id, message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Leaderboard command processed"}),
        }
    except Exception as e:
        logger.error(f"Failed to send leaderboard message: {e}")
        error_message = "An error occurred while processing the leaderboard command. Please try again later."
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


async def send_text2vote(update, context):
    user_id = update.effective_user.id
    await set_user_data(user_id, "auto_vote", "True")

    translation_id = await get_user_data(user_id, "translation_id")

    if translation_id:
        # If a translation_id is available in user_data, fetch the corresponding translation
        result = await get_translation_by_id(translation_id)

        if not result:
            # If the translation is not found, set translation_id to None and proceed to fetch a new translation
            await set_user_data(user_id, "translation_id", None)
            translation_id = None

    if not translation_id:
        result = await get_unvoted_translation()
        if result:
            await set_user_data(user_id, "translation_id", result["id"])

    if result:
        original_text_id = result["original_text_id"]
        translation_text = result["text"]

        original_text = await get_original_text(original_text_id)

        message = f"Please rate the following translation:\n\nEnglish: {original_text}\n\nMyanmar: {translation_text}"

        keyboard = [
            [
                InlineKeyboardButton(
                    str(score), callback_data=f"vote_{result['id']}_{score}"
                )
                for score in range(1, 6)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        message = "No translations available for voting at the moment. Please try again later."
        reply_markup = None

    try:
        await send_message(user_id, message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to send voting message: {e}")
        error_message = "An error occurred while sending the voting message. Please try again later."
        await send_message(user_id, error_message)
