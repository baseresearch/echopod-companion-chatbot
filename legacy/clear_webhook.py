import os
import requests
from dotenv import load_dotenv

# Quick helper script to clear the pending_update_count
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
# Get the latest update ID
response = requests.get(URL)
updates = response.json().get("result", [])
if updates:
    last_update_id = updates[-1]["update_id"]

    # Clear pending updates by setting offset to last_update_id + 1
    requests.get(URL, params={"offset": last_update_id + 1})