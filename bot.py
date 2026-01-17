import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

# --- PART 1: FAKE WEBSITE (To keep Render awake) ---
# This tricks the free server into thinking this is a website so it doesn't crash.
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_server():
    # Render expects a web server on port 8080 (or process.env.PORT)
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Start the fake server in the background
threading.Thread(target=start_server, daemon=True).start()

# --- PART 2: YOUR BOT CODE ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# YOUR TOKEN IS HERE
BOT_TOKEN = "8503783055:AAGM5zPrqwMTnuPUwY4FStJtge0WDdB8N0I"

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Get the link
    url = update.message.text
    user_first_name = update.effective_user.first_name
    
    # 2. Tell user to wait
    status_msg = await update.message.reply_text(f"⏳ Processing
