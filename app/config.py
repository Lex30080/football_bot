import os
from dotenv import load_dotenv

load_dotenv()



BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")

ADMINS = {490874415} # NEED TO ADD ROMIK AND ANDREY