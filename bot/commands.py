import json
import logging
from db import (
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
from utils import send_message, handle_command_error
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"start_command called with update: {update}, context: {context}")
    user_id = update.effective_user.id
    username = update.effective_user.full_name

    try:
        is_user_exists(user_id, username)
        message = "Welcome to the Echopod Builder!\n\nTo get started, please send:\n\n1. /contribute\n2. /vote"
        await send_message(context, user_id, message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Start command processed"}),
        }
    except Exception as e:
        return await handle_command_error(update, context, e, "start")


async def contribute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"contribute_command called with update: {update}, context: {context}")
    user_id = update.effective_user.id
    set_user_data(user_id, "contribute_mode", "True")
    set_user_data(user_id, "auto_contribute", "True")
    set_user_data(user_id, "paused", "False")

    try:
        result = get_untranslated_text()

        if result:
            message = f"Please translate the following English sentence to Burmese:\n\n{result['text']}"
            set_user_data(user_id, "contribute_text_id", result["text_id"])
        else:
            message = "No untranslated sentences available at the moment. Please try again later."

        keyboard = [[InlineKeyboardButton("Skip", callback_data="skip_contribute")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await send_message(context, user_id, message, reply_markup=reply_markup)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Contribute command processed"}),
        }
    except Exception as e:
        return await handle_command_error(update, context, e, "contribute")


async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"vote_command called with update: {update}, context: {context}")
    user_id = update.effective_user.id
    try:
        set_user_data(user_id, "auto_vote", "False")
        set_user_data(user_id, "paused", "False")

        # Check if this is the first time the user is using the /vote command
        saw_best_practices = get_user_data(user_id, "saw_best_practices")
        logger.info(f"saw_best_practices: {saw_best_practices}")

        if not saw_best_practices:
            logger.info(
                f"saw_best_practices called with update: {update}, context: {context}"
            )
            set_user_data(user_id, "saw_best_practices", "True")

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

            await send_message(
                context, user_id, voting_rules, reply_markup=reply_markup
            )
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
        return await handle_command_error(update, context, e, "vote")


async def send_text2vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"send_text2vote called with update: {update}, context: {context}")
    user_id = update.effective_user.id

    set_user_data(user_id, "auto_vote", "True")

    translation_id = get_user_data(user_id, "translation_id")
    if translation_id:
        result = get_translation_by_id(translation_id)
    else:
        result = get_unvoted_translation()
        if result:
            set_user_data(user_id, "translation_id", result["id"])

    if result:
        original_text_id = result["original_text_id"]
        translation_text = result["text"]
        original_text = get_original_text(original_text_id)

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

    await send_message(context, user_id, message, reply_markup=reply_markup)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Vote command processed"}),
    }


async def simple_vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    set_user_data(user_id, "vote_mode", "True")
    set_user_data(user_id, "auto_vote", "True")
    set_user_data(user_id, "paused", "False")

    try:
        result = get_unvoted_translation()
        if result:
            original_text_id = result["original_text_id"]
            original_text = get_original_text(original_text_id)
            translation = result["text"]
            message = f"Please vote on the following translation:\n\nEnglish: {original_text}\nBurmese: {translation}"
            set_user_data(user_id, "vote_translation_id", result["id"])
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
            await send_message(context, user_id, message, reply_markup=reply_markup)
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Vote command processed"}),
            }
        except Exception as e:
            return await handle_command_error(update, context, e, "simple_vote")

    except Exception as e:
        return await handle_command_error(update, context, e, "simple_vote")


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"leaderboard_command called with update: {update}, context: {context}")
    try:
        leaderboard_data = get_leaderboard_data()

        if leaderboard_data:
            message = "Top 10 Contributors:\n\n"
            for i, item in enumerate(leaderboard_data, start=1):
                try:
                    user_details = get_user_details(item["user_id"])
                    username = user_details["username"] if user_details else "Unknown"
                except Exception as e:
                    logger.error(f"Error in get_user_details: {e}")
                    username = "Unknown"
                message += f"{i}. {username} - {item['score']} points\n"
        else:
            message = "No leaderboard data available at the moment."

        try:
            await send_message(context, update.effective_user.id, message)
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Leaderboard command processed"}),
            }
        except Exception as e:
            return await handle_command_error(update, context, e, "leaderboard")

    except Exception as e:
        return await handle_command_error(update, context, e, "leaderboard")


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"stop_command called with update: {update}, context: {context}")
    user_id = update.effective_user.id

    set_user_data(user_id, "auto_contribute", "False")
    set_user_data(user_id, "auto_vote", "False")
    set_user_data(user_id, "paused", "True")

    try:
        message = "Please use /contribute or /vote to start again."
        await send_message(context, user_id, message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Stop command processed"}),
        }
    except Exception as e:
        return await handle_command_error(update, context, e, "stop")
