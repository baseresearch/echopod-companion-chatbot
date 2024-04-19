import json
import logging
from db import (
    get_user_data,
    set_user_data,
    is_user_exists,
    get_untranslated_text,
    get_unvoted_translation,
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
        set_user_data(user_id, "auto_vote", "True")
        set_user_data(user_id, "paused", "False")

        # Check if this is the first time the user is using the /vote command
        saw_best_practices = get_user_data(user_id, "saw_best_practices")
        logger.info(f"saw_best_practices: {saw_best_practices}")

        if saw_best_practices != "True":
            logger.info(
                f"saw_best_practices called with update: {update}, context: {context}"
            )
            set_user_data(user_id, "saw_best_practices", "True")

            voting_rules = (
                "Before you start voting, here are some best practices to keep in mind:\n\n"
                "1. Evaluate the translation based on its accuracy, fluency, and clarity.\n"
                "2. Avoid voting based on personal preferences or opinions.\n"
                "3. If you're unsure about a translation, skip it and move on to the next one.\n"
                "4. Take breaks between voting sessions to avoid fatigue and maintain quality.\n\n"
                "Happy voting! 🗳️"
            )

            keyboard = [
                [InlineKeyboardButton("Start Voting", callback_data="start_voting")]
            ]
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
    user_id = update.effective_user.id
    try:
        result = get_unvoted_translation()

        if result:
            original_text = result["original_text"]
            translation_text = result["text"]
            translation_id = result["translation_id"]

            message = (
                f"English:\n{original_text}\n\n"
                f"Myanmar:\n{translation_text}\n\n"
                "How would you rate this translation?"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        str(score), callback_data=f"vote_{translation_id}_{score}"
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
    except Exception as e:
        return await handle_command_error(update, context, e, "send_text2vote")


async def simple_vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"simple_vote_command called with update: {update}, context: {context}")
    user_id = update.effective_user.id

    try:
        set_user_data(user_id, "auto_vote", "True")
        set_user_data(user_id, "paused", "False")

        result = get_unvoted_translation()

        if result:
            original_text = result["original_text"]
            translation_text = result["text"]
            translation_id = result["translation_id"]

            message = (
                f"Original Text:\n{original_text}\n\n"
                f"Translated Text:\n{translation_text}\n\n"
                "How would you rate this translation?"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "👎", callback_data=f"vote_{translation_id}_-1"
                    ),
                    InlineKeyboardButton(
                        "👌", callback_data=f"vote_{translation_id}_0"
                    ),
                    InlineKeyboardButton(
                        "👍", callback_data=f"vote_{translation_id}_1"
                    ),
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
    except Exception as e:
        return await handle_command_error(update, context, e, "simple_vote")


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"leaderboard_command called with update: {update}, context: {context}")
    try:
        leaderboard_data = get_leaderboard_data()

        if leaderboard_data:
            message = "🐬 Top 10 Users:\n\n"
            for i, item in enumerate(leaderboard_data, start=1):
                username = item["username"]
                score = item["score"]
                message += f"{i}. {username} - {score} points\n"
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
