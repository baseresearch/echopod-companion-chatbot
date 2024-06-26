from datetime import datetime
import json
import logging
from bot.utils import (
    send_message,
    edit_message_reply_markup,
    calculate_interaction_interval,
    update_avg_interaction_interval,
)
from bot.db import (
    execute_db_query_async,
    get_user_data,
    set_user_data,
    translation_table,
    score_table,
)
from bot.commands import contribute_command, send_text2vote

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
