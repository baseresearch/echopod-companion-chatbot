import asyncio
import json
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from callbacks import (
    handle_text,
    handle_contribution,
    handle_skip_contribution,
    handle_start_voting,
    handle_vote,
)
from commands import (
    start_command,
    contribute_command,
    vote_command,
    leaderboard_command,
    stop_command,
)
from config import TELEGRAM_BOT_TOKEN

def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(main(event, context))


async def main(event, context):
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

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

    try:
        await application.initialize()
        await application.process_update(
            Update.de_json(json.loads(event["body"]), application.bot)
        )

        return {"statusCode": 200, "body": "Success"}

    except Exception as exc:
        return {"statusCode": 500, "body": "Failure"}
