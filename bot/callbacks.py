import json
import logging
from datetime import datetime
from commands import contribute_command, send_text2vote
from db import (
    get_user_data,
    set_user_data,
    save_contribution,
    save_vote,
    get_original_text,
)
from utils import (
    send_message,
    edit_message_reply_markup,
    calculate_interaction_interval,
    update_avg_interaction_interval,
    check_threshold,
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    interaction_interval = calculate_interaction_interval(user_id)
    update_avg_interaction_interval(user_id, interaction_interval)
    set_user_data(user_id, "last_interaction_time", datetime.now().isoformat())

    contribute_mode = get_user_data(user_id, "contribute_mode")
    if contribute_mode == "True":
        await handle_contribution(update, context)
    else:
        message = "Please use the provided commands to interact with the bot."
        await send_message(context, user_id, message)

    return {"statusCode": 200, "body": json.dumps({"message": "Text handled"})}


async def handle_contribution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    contribution_interval = calculate_interaction_interval(user_id)
    update_avg_interaction_interval(user_id, contribution_interval)
    set_user_data(user_id, "last_interaction_time", datetime.now().isoformat())

    text_id = get_user_data(user_id, "contribute_text_id")
    if not text_id:
        await send_message(
            context,
            user_id,
            "No contribution context found. Please use the /contribute command to start contributing.",
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Contribution handled"}),
        }

    try:
        original_text = get_original_text(text_id)
        save_contribution(text_id, user_id, "mya", update.message.text, original_text)
        message = "Thank you for your contribution!"
    except Exception:
        logger.exception("Failed to save contribution")
        message = (
            "Failed to save your contribution due to an error. Please try again later."
        )

    set_user_data(user_id, "contribute_mode", "False")
    threshold, threshold_message = check_threshold(user_id, type="contribution")

    if threshold:
        keyboard = [
            [
                InlineKeyboardButton("Continue", callback_data="skip_contribute")
            ]  # We reuse skip
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await send_message(
            context, user_id, threshold_message, reply_markup=reply_markup
        )
    else:
        await send_message(context, user_id, message)

        if get_user_data(user_id, "auto_contribute") == "True":
            await contribute_command(update, context)

    return {"statusCode": 200, "body": json.dumps({"message": "Contribution handled"})}


async def handle_skip_contribution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    interaction_interval = calculate_interaction_interval(user_id)
    update_avg_interaction_interval(user_id, interaction_interval)
    set_user_data(user_id, "last_interaction_time", datetime.now().isoformat())

    query = update.callback_query
    query.answer()

    if query.data == "skip_contribute":
        await contribute_command(update, context)


async def handle_start_voting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        voting_interval = calculate_interaction_interval(user_id)
        update_avg_interaction_interval(user_id, voting_interval)
        set_user_data(user_id, "last_interaction_time", datetime.now().isoformat())

        query = update.callback_query
        query.answer()

        if query.data == "start_voting":
            await edit_message_reply_markup(
                context,
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
        logger.exception("Error handling start voting")
        error_message = "An error occurred while starting the voting process. Please try again later."
        await send_message(context, user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error handling start voting"}),
        }


async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        voting_interval = calculate_interaction_interval(user_id)
        update_avg_interaction_interval(user_id, voting_interval)
        set_user_data(user_id, "last_interaction_time", datetime.now().isoformat())

        query = update.callback_query
        await query.answer()

        translation_id, score = query.data.split("_")[1:]
        save_vote(translation_id, user_id, score)

        threshold, threshold_message = check_threshold(user_id, type="vote")
        if threshold:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Continue Voting", callback_data="continue_voting"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await send_message(
                context, user_id, threshold_message, reply_markup=reply_markup
            )
        else:
            await edit_message_reply_markup(
                context,
                update.effective_chat.id,
                query.message.message_id,
                None,
            )
            auto_vote = get_user_data(user_id, "auto_vote")
            if auto_vote == "True":
                await send_text2vote(update, context)

        return {"statusCode": 200, "body": json.dumps({"message": "Vote handled"})}
    except Exception as e:
        logger.exception("Error handling vote")
        error_message = (
            "An error occurred while processing your vote. Please try again later."
        )
        await send_message(context, user_id, error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Error handling vote"}),
        }
