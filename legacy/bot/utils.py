from datetime import datetime, timedelta
import logging
from telegram import Bot
from bot.db import execute_db_query_async, get_user_data, set_user_data, user_data_table
from bot.config import TELEGRAM_BOT_TOKEN
from bot.config import VOTING_SESSION_THRESHOLD

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
