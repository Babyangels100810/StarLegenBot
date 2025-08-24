# config.py — միայն կոնֆիգ
import os

# Bot token — պահիր Env Var-ում (Render/Railway):
# TELEGRAM_TOKEN
BOT_TOKEN = os.getenv( "8054385688:AAG1rSbhOeZmGZ5ZFIeCEZZhxOpnQdbK5ZM", "").strip()

# Հոսթը ավտոմատ վերցնենք հարթակից.
# Render → RENDER_EXTERNAL_URL, Railway → RAILWAY_PUBLIC_DOMAIN
_render = os.getenv("RENDER_EXTERNAL_URL", "").strip()
_rail   = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

if _render:
    WEBHOOK_HOST = f"https://{_render.replace('https://', '').replace('http://','')}"
elif _rail:
    WEBHOOK_HOST = f"https://{_rail.replace('https://', '').replace('http://','')}"
else:
    # fallback՝ եթե վերևից ոչինչ չկա, դնում ենք ձեռքով (ՓՈԽԱՐԻՆԵԼ քո դոմեյնով)
    WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://<your-app>.up.railway.app").strip()

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL  = WEBHOOK_HOST + WEBHOOK_PATH

