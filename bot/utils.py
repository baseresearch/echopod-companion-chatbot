import logging
import json
from datetime import datetime
from db import get_user_data, set_user_data
from config import VOTING_SESSION_THRESHOLD

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


async def send_reminder_message(context, user_id):
    message = "Hi! It's been a while since your last voting session.\n\nYour votes help ensure the quality of the 🐬 Echopod dataset.\n\nTake a moment to review some translations today! 🙏🐬"
    await send_message(context, user_id, message)


async def send_message(context, user_id, message, reply_markup=None):
    try:
        await context.bot.send_message(
            chat_id=user_id, text=message, reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending message to user {user_id}: {e}")


async def edit_message_reply_markup(context, chat_id, message_id, reply_markup):
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message reply markup: {e}")


async def handle_command_error(context, error, command_name, user_id):
    logger.error(f"Failed to process {command_name} command: {error}")
    error_message = f"An error occurred while processing the {command_name} command. Please try again later."
    await send_message(context, user_id, error_message)
    return {
        "statusCode": 500,
        "body": json.dumps({"message": f"Error processing {command_name} command"}),
    }


def calculate_interaction_interval(user_id):
    current_time = datetime.now()
    last_interaction_time = get_user_data(user_id, "last_interaction_time")
    last_interaction_session_time = get_user_data(
        user_id, "last_interaction_session_time"
    )

    if last_interaction_time:
        last_interaction_time = datetime.fromisoformat(last_interaction_time)
        if (
            current_time - last_interaction_time
        ).total_seconds() <= VOTING_SESSION_THRESHOLD:
            set_user_data(
                user_id, "last_interaction_session_time", current_time.isoformat()
            )
            return None
        else:
            voting_interval = (
                current_time - datetime.fromisoformat(last_interaction_session_time)
            ).total_seconds()
            set_user_data(
                user_id, "last_interaction_session_time", current_time.isoformat()
            )
            return voting_interval
    else:
        set_user_data(
            user_id, "last_interaction_session_time", current_time.isoformat()
        )
        return None


def update_avg_interaction_interval(user_id, interval):
    default_interval = 24 * 60 * 60  # 24 hours in seconds

    avg_interval = get_user_data(user_id, "avg_interaction_interval")
    avg_interval = (
        float(avg_interval)
        if avg_interval and avg_interval != "None"
        else default_interval
    )

    new_avg_interval = (avg_interval + interval) / 2 if interval else avg_interval

    set_user_data(user_id, "avg_interaction_interval", str(new_avg_interval))
