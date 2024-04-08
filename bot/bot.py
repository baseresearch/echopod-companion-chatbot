import os
import asyncio
import psycopg2
import psycopg2.pool
import logging
from contextlib import contextmanager
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database connection parameters using environment variables
db_params = {
    "minconn": 1,
    "maxconn": 20,
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
}

# Initialize a connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(**db_params)

# Replace with your own token for testing / development
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# Context manager for database connections
@contextmanager
def db_connection():
    """Context manager for database connections."""
    try:
        conn = db_pool.getconn()
        yield conn
    except Exception as e:
        logger.error(f"Failed to get DB connection: {e}")
        raise
    finally:
        if conn:
            db_pool.putconn(conn)


def execute_db_query(query, params=None, fetchone=False, fetchall=False):
    """Executes a database query with optional parameters.

    Args:
        query (str): SQL query to execute.
        params (tuple, optional): Parameters for the SQL query.
        fetchone (bool, optional): Whether to fetch one row. Defaults to False.
        fetchall (bool, optional): Whether to fetch all rows. Defaults to False.

    Returns:
        tuple or list: The result of the query.

    Raises:
        Exception: If the query execution fails.
    """
    with db_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetchone:
                    return cur.fetchone()
                if fetchall:
                    return cur.fetchall()
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error during query execution: {e}")
            raise


async def execute_db_query_async(query, params=None, fetchone=False, fetchall=False):
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None,  # Uses the default executor
            lambda: execute_db_query(query, params, fetchone, fetchall),
        )
        return result
    except Exception as e:
        logger.error(f"Async DB query execution failed: {e}")
        raise


async def is_user_exists(user_id, username):
    user_exists_query = 'SELECT EXISTS(SELECT 1 FROM "User" WHERE user_id = %s)'
    user_exists = await execute_db_query_async(
        user_exists_query, (user_id,), fetchone=True
    )

    if not user_exists[0]:
        await add_new_user(user_id, username)


async def add_new_user(user_id, username):
    insert_user_query = 'INSERT INTO "User" (user_id, username) VALUES (%s, %s)'
    await execute_db_query_async(insert_user_query, (user_id, username))


async def start_command(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.full_name
    try:
        await is_user_exists(user_id, username)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Welcome to the Echopod Builder!\n\nTo get started, please send:\n\n1. /contribute\n2. /vote",
        )
    except Exception as e:
        logger.error(f"Failed to send start message: {e}")


async def contribute_command(update, context):
    context.user_data["contribute_mode"] = True
    context.user_data["auto_contribute"] = True

    query = """
    SELECT text_id, text 
    FROM OriginalText 
    WHERE text_id NOT IN (SELECT original_text_id FROM Translation) 
    ORDER BY RANDOM() 
    LIMIT 1
    """
    result = await execute_db_query_async(query, fetchone=True)
    message = (
        "No untranslated sentences available at the moment. Please try again later."
        if not result
        else f"Please translate the following English sentence to Burmese:\n\n{result[1]}"
    )

    if result:
        context.user_data["contribute_text_id"] = result[0]

    keyboard = [[InlineKeyboardButton("Skip", callback_data="skip_contribute")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup
    )


async def vote_command(update, context):
    context.user_data["auto_vote"] = True

    query = """
    SELECT t.translation_id, o.text AS original_text, t.text AS translated_text 
    FROM Translation t 
    JOIN OriginalText o ON t.original_text_id = o.text_id 
    ORDER BY RANDOM() 
    LIMIT 1
    """
    result = await execute_db_query_async(query, fetchone=True)
    message = (
        "No translations available for scoring at the moment. Please try again later."
        if not result
        else f"Please rate the quality of the following translation (1-5):\n\nEnglish: {result[1]}\n\nBurmese: {result[2]}"
    )

    if result:
        context.user_data["score_translation_id"] = result[0]

    keyboard = [
        [
            InlineKeyboardButton(
                str(score), callback_data=f"vote_{result[0]}_{score}"
            )  # voting callback
            for score in range(1, 6)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup,
    )


async def leaderboard_command(update, context):
    query = """
    SELECT u.username, COUNT(*) AS contribution_count 
    FROM Translation t 
    JOIN "User" u ON t.user_id = u.user_id 
    GROUP BY u.username 
    ORDER BY contribution_count DESC 
    LIMIT 10
    """
    result = await execute_db_query_async(query, fetchall=True)
    if result:
        leaderboard_text = "Top 10 Contributors:\n\n" + "\n".join(
            f"{rank}. {username}: {count} contributions"
            for rank, (username, count) in enumerate(result, start=1)
        )
    else:
        leaderboard_text = "No contributions found."

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=leaderboard_text
    )


async def stop_command(update, context):
    context.user_data["auto_contribute"] = False
    context.user_data["auto_vote"] = False
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please use /contribute or /vote to start again.",
    )


async def handle_text(update, context):
    # Check if the user is in contribution mode
    if "contribute_mode" in context.user_data and context.user_data["contribute_mode"]:
        # Handle the contribution
        await handle_contribution(update, context)
    else:
        # Inform the user that text input is not expected at this moment
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please use the provided commands to interact with the bot.",
        )


async def handle_contribution(update, context):
    user_id = update.effective_user.id
    text_id = context.user_data.get("contribute_text_id")
    translated_text = update.message.text

    if not text_id:
        message = "No contribution context found. Please use the /contribute command to start contributing."
    else:
        query = """
        INSERT INTO Translation (original_text_id, user_id, lang, text)
        VALUES (%s, %s, 'my', %s)
        """
        params = (text_id, user_id, translated_text)
        try:
            await execute_db_query_async(query, params)
            message = "Thank you for your contribution!"
        except Exception as e:
            message = f"Failed to save your contribution due to an error: {e}"

    # Reset the contribution mode
    context.user_data["contribute_mode"] = False

    # After saving the contribution or handling errors
    message = "Thank you for your contribution!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    # Check if auto_contribute mode is enabled, then automatically fetch the next item for contribution
    if context.user_data.get("auto_contribute", False):
        await contribute_command(update, context)


async def handle_skip_contribution(update, context):
    query = update.callback_query  # handle "Skip" contribution callback
    await query.answer()

    if query.data == "skip_contribute":
        await contribute_command(update, context)


async def handle_vote(update, context):
    query = update.callback_query  # handle user voting callback
    await query.answer()

    logger.info(f"Received vote callback: {query.data}")

    data_parts = query.data.split("_")

    if len(data_parts) != 3:
        logger.error(f"Unexpected callback data format: {query.data}")
        # Optionally, send a message to the user about the unexpected error
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="An unexpected error occurred. Please try again.",
        )
        return

    _, translation_id, score_value = data_parts
    user_id = update.effective_user.id
    score_value = int(score_value)

    # Now, you can insert the score into the database as before
    insert_query = """
    INSERT INTO Score (translation_id, user_id, score_value) VALUES (%s, %s, %s)
    """
    await execute_db_query_async(insert_query, (translation_id, user_id, score_value))

    # After processing the vote, remove the keyboard
    await context.bot.edit_message_reply_markup(
        chat_id=update.effective_chat.id,
        message_id=query.message.message_id,
        reply_markup=None,
    )

    # After processing the vote
    message = "Thank you for your rating!"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    # Check if auto_vote mode is enabled, then automatically fetch the next item for voting
    if context.user_data.get("auto_vote", False):
        await vote_command(update, context)

    # TODO if score is below 3, ask for alternate translation
    # if score_value < 3:
    #     delete_query = """
    #     DELETE FROM Translation WHERE translation_id = %s
    #     """
    #     await execute_db_query_async(delete_query, (translation_id,))
    #     message += "\nThe translation has been removed due to a low score and will be available for contribution again."


def main():
    # Create an Application instance
    application = Application.builder().token(TOKEN).build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("contribute", contribute_command))
    application.add_handler(CommandHandler("vote", vote_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
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
    application.run_polling()


if __name__ == "__main__":
    main()
