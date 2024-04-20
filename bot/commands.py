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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.full_name

    try:
        is_user_exists(user_id, username)
        message = "🐬\nWelcome to the Echopod Companion!\n\nTo get started, please send:\n\n1. /contribute\n2. /vote"
        await send_message(context, user_id, message)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Start command processed"}),
        }
    except Exception as e:
        return await handle_command_error(update, context, e, "start")


async def contribute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    set_user_data(user_id, "contribute_mode", "True")
    set_user_data(user_id, "auto_contribute", "True")
    set_user_data(user_id, "paused", "False")

    try:
        result = get_untranslated_text()

        if result:
            message = f"🐬\nဒီစာကို အဆင်ပြေသလို ဘာသာပြန်ပေးပါ\n\n-⚠️မြန်မာစကားပြောအရေးအသားနဲ့ပဲ ရေးပေးပါနော်⚠️-\n\n{result['text']}"
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
    user_id = update.effective_user.id
    try:
        set_user_data(user_id, "auto_vote", "True")
        set_user_data(user_id, "paused", "False")

        # Check if this is the first time the user is using the /vote command
        saw_best_practices = get_user_data(user_id, "saw_best_practices")

        if saw_best_practices != "True":
            set_user_data(user_id, "saw_best_practices", "True")

            voting_rules = (
                "🐬\nအမှတ်ပေးတဲ့အခါမှာ ဒီအချက်တွေကို သတိပြုပေးပါခင်ဗျာ-\n\n"
                "အခုဒေတာစုက အင်္ဂလိပ်<->မြန်မာ 'စကားပြော'အရေးအသားကို အဓိကထားပါတယ်\n\n"
                "တစ်ချို့စကားလုံးတွေကို ဆီလျော်အောင် ဘာသာပြန်ထားတာဖြစ်လို့၊​ အဓိပ္ပါယ်တူသရွေ့ အဆင်ပြေပါတယ်\n\n"
                "ဘန်းစကားသုံးထားတာတွေ တစ်ခါတစ်လေ ပါလာနိုင်ပါတယ်\n\n"
                "ကိုယ့်အကြိုက် ဒါမှမဟုတ် ထင်မြင်ယူဆချက်ပေါ်မှာ အခြေခံပြီး အမှတ်မပေးပါနဲ့ခင်ဗျာ\n\n"
                "လုံးဝမှားနေမှ ၁ ကို ပေးပါ\n\n"
                "စာလုံးပေါင်း အနည်းငယ်မှားရုံပဲဆိုရင် ၂ က စပြီးပေးပေးပါ\n\n"
                "အရေးအကြီးဆုံးကတော့... လူမပင်ပန်းအောင် နားနားပြီး vote ပါနော် 🗳️"
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
                f"🐬\n"
                + "အောက်ပါဘာသာပြန်ဆိုမှုအား 1 မှ 5 အတွင်း အဆင့်သတ်မှတ်ပေးပါ:\n\n"
                + "English:\n----------| "
                + f"{original_text}\n\n"
                + "Burmese:\n----------| "
                + f"{translation_text}\n\n"
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
