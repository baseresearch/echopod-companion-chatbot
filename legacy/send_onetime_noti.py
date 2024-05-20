import os
from dotenv import load_dotenv
from telegram import Bot

# Quick helper script to clear the pending_update_count
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
# List of user IDs of existing users
existing_user_ids = [
    222654113,
    1453348045,
    59612127,
    956546107,
    62599823,
    1658355839,
    364988157,
    652049624,
    1630673508,
    2102637623,
    180847183,
    272079293,
    1612825807,
    50660826,
    1004461609,
    660085727,
    132595403,
    787324774,
    1140572376,
    477495120,
]

# Message to send to existing users
message = "Hi! It's been a while since your last voting session.\n\nYour votes help ensure the quality of the 🐬 Echopod dataset.\n\nTake a moment to review some translations today! 🙏🐬"


async def send():
    # Send the message to all existing users
    for user_id in existing_user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {e}")


async def main():
    await send()


# Run the main function
import asyncio

asyncio.run(main())
