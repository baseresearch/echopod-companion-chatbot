import json
import logging
from telegram import Update
from bot.callbacks import (
    handle_text,
    handle_skip_contribution,
    handle_start_voting,
    handle_vote,
)
from bot.commands import (
    start_command,
    contribute_command,
    vote_command,
    leaderboard_command,
    stop_command,
)
from bot.utils import reminder_job

logger = logging.getLogger()
logger.setLevel(logging.INFO)

event_handlers = {
    "start": start_command,
    "contribute": contribute_command,
    "vote": vote_command,
    "leaderboard": leaderboard_command,
    "stop": stop_command,
    "text": handle_text,
    "skip_contribute": handle_skip_contribution,
    "start_voting": handle_start_voting,
    "vote": handle_vote,
}


async def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        # Handle CloudWatch Events trigger for reminder job
        try:
            await reminder_job(event, context)
        except Exception as e:
            logger.error(f"Error in reminder_job: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    else:
        try:
            logger.info(f"Received event: {event}")

            if "body" in event:
                update = Update.de_json(json.loads(event["body"]), None)
                if update.message:
                    if update.message.text.startswith("/"):
                        command = update.message.text[1:].split("@")[0]
                        handler = event_handlers.get(command)
                    else:
                        handler = event_handlers.get("text")
                elif update.callback_query:
                    query = update.callback_query
                    handler = event_handlers.get(query.data.split("_")[0])

                if handler:
                    response = await handler(update, context)
                else:
                    response = {
                        "statusCode": 400,
                        "body": json.dumps({"error": "Invalid command or query"}),
                    }
            else:
                response = {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid request"}),
                }

            return response
        except Exception as e:
            logger.error(f"Error in lambda_handler: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
