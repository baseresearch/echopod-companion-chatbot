import logging
import json
from datetime import datetime
from db import get_user_data, set_user_data, get_aggregated_counts
from config import VOTING_SESSION_THRESHOLD

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.ERROR)


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
            chat_id=chat_id, message_id=message_id, reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message reply markup: {e}")


async def handle_command_error(context, error, command_name, user_id):
    logger.error(f"Error in {command_name} command: {error}")
    error_message = f"An error occurred while processing the {command_name} command. Please try again later."
    await send_message(context, user_id, error_message)
    return {
        "statusCode": 500,
        "body": json.dumps({"message": f"Error in {command_name} command"}),
    }


def check_threshold(user_id, type="contribution"):
    today = datetime.now().strftime("%Y-%m-%d")
    total_translations, total_votes = get_aggregated_counts(today, user_id)

    milestones = {
        "contribution": {
            10: "🐬\nကျေးဇူးတင်ပါတယ်!\n\nခဏလောက် မျက်စိအနားပေးလိုက်ပါဦးနော်...😌",
            25: "🐬\n၁၀ မိနစ်လောက် နားဦးလေ\n\nတစ်ထိုင်ထဲ အများကြီးလုပ်ရင် ပင်ပန်းနေမှာစိုးလို့ပါ ❤️",
            35: "🐬\nကျေးဇူးအများကြီးတင်ပါတယ်!\n\nဒီနေ့အတွက် နားမယ်ဆိုရင်၊ နားလိုက်တော့နော်...\nတစ်ထိုင်ထဲ အများကြီးလုပ်ရင် ပင်ပန်းမှာစိုးလို့ပါ ❤️",
            50: "🐬\nကဲ.. မနားသေးဘူးကိုး\n\nဒီနေ့အတွက် {count}ခုတောင် ဘာသာပြန်ပေးထားတာ...\n\nနားလိုက်ပါတော့နော်...❤️\n\nတစ်နေ့ကိုနည်းနည်းစီ ပုံမှန်လုပ်ဖို့က ပိုအရေးကြီးတာမလို့၊ မနက်ဖြန်ကြရင်ထပ်တွေ့မယ်လေ... ❤️",
        },
        "vote": {
            10: "🐬\nကျေးဇူးတင်ပါတယ်!\n\nခဏလောက် မျက်စိအနားပေးလိုက်ပါဦးနော်...😌",
            30: "🐬\n၅ မိနစ်လောက် နားဦးလေ\n\nတစ်ထိုင်ထဲ အများကြီးလုပ်ရင် ပင်ပန်းနေမှာစိုးလို့ပါ ❤️",
            50: "🐬\nကျေးဇူးအများကြီးတင်ပါတယ်!\n\nဒီနေ့အတွက် {count}တောင်အမှတ်ပေးလိုက်တာ...\n\nနားမယ်ဆိုရင်၊ နားလိုက်တော့နော်...❤️\n\nတစ်နေ့ကိုနည်းနည်းစီ ပုံမှန်လုပ်ဖို့က ပိုအရေးကြီးတာမလို့၊ မနက်ဖြန်ကြရင်ထပ်တွေ့မယ်လေ...",
            100: "🐬\nကဲ.. မနားသေးဘူးကို\nကျေးဇူးအများကြီးတင်ပါတယ်ဗျာ!\n\nဒါပေမယ့် ဒီတစ်ခါတော့ တကယ်နားလိုက်ပါတော့\n\nဒီနေ့အတွက် {count}ခုတောင် အမှတ်ပေးပြီးသွားပြီလေ...\n\nနားလိုက်ပါတော့.. လိမ္မာပါတယ်..\n\nမနက်ဖြန်ကြရင်တော့ ထပ်ပြီးကူပေးဖို့ မမေ့ရဘူးနော်...",
        },
    }

    count = int(total_translations) if type == "contribution" else int(total_votes)

    if count in milestones[type]:
        milestone_message = milestones[type][count].format(count=count)
        return True, milestone_message

    return False, None


def calculate_interaction_interval(user_id):
    current_time = datetime.now()
    last_interaction_time = get_user_data(user_id, "last_interaction_time")
    last_interaction_session_time = get_user_data(
        user_id, "last_interaction_session_time"
    )

    if last_interaction_time:
        last_interaction_time = datetime.fromisoformat(last_interaction_time)
        interaction_interval = (current_time - last_interaction_time).total_seconds()
    else:
        interaction_interval = None

    if last_interaction_session_time:
        last_interaction_session_time = datetime.fromisoformat(
            last_interaction_session_time
        )
        session_interval = (
            current_time - last_interaction_session_time
        ).total_seconds()

        if session_interval > VOTING_SESSION_THRESHOLD:
            set_user_data(
                user_id, "last_interaction_session_time", current_time.isoformat()
            )
            return interaction_interval
        else:
            return None
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
