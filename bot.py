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
    status_msg = await update.message.reply_text(f"⏳ Processing link for {user_first_name}...\nPlease wait (this can take 10-30 seconds).")

    # 3. Configure Download Options
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Best Quality
        'outtmpl': 'downloads/%(id)s.%(ext)s', # Save to 'downloads' folder
        'noplaylist': True,                    # Single video only
        'cookiefile': 'cookies.txt',           # (Optional) Helps with some sites, harmless if missing
    }

    try:
        # 4. Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Video')
            # Find the file path
            filename = f"downloads/{info['id']}.{info['ext']}"

        # 5. Upload to Telegram
        await update.message.reply_text(f"✅ Download complete!\nSending file...")
        
        with open(filename, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption=video_title)

        # 6. Delete file to save space
        if os.path.exists(filename):
            os.remove(filename)
        
        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}\n(Try a different link or check if the video is private)")
        print(f"Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hi! Send me a link from Instagram, YouTube, or Facebook.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler('start', start))
    
    # Message Handler (Everything that is NOT a command)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_video))
    
    print("Bot is starting...")
    application.run_polling()
