import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

# --- PART 1: FAKE WEBSITE (To keep Render awake) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# --- PART 2: BOT CODE ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# YOUR TOKEN
BOT_TOKEN = "8503783055:AAGM5zPrqwMTnuPUwY4FStJtge0WDdB8N0I"

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_first_name = update.effective_user.first_name
    
    # Notify user
    status_msg = await update.message.reply_text(f"⏳ Processing for {user_first_name}...\n(Downloading Thumbnail & Video)")

    # NEW: Options to get the thumbnail and convert it to JPG
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'writethumbnail': True,  # Ask for thumbnail
        'postprocessors': [{     # Convert thumbnail to JPG (Telegram likes JPG)
            'key': 'FFmpegThumbnailsConvertor',
            'format': 'jpg',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Video')
            video_id = info.get('id')
            ext = info.get('ext')
            
            video_filename = f"downloads/{video_id}.{ext}"
            thumb_filename = f"downloads/{video_id}.jpg" # yt-dlp saves it as .jpg

        await update.message.reply_text(f"✅ Download complete!\nUploading {video_title}...")
        
        # NEW: Send Video WITH Thumbnail and Increased Timeout
        with open(video_filename, 'rb') as video_file:
            # Check if thumbnail exists
            if os.path.exists(thumb_filename):
                with open(thumb_filename, 'rb') as thumb_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=video_title,
                        thumbnail=thumb_file,
                        write_timeout=60,  # WAIT 60 SECONDS (Fixes Timeout Error)
                        read_timeout=60
                    )
            else:
                # Fallback if no thumbnail found
                await update.message.reply_video(
                    video=video_file,
                    caption=video_title,
                    write_timeout=60,
                    read_timeout=60
                )

        # Cleanup
        if os.path.exists(video_filename): os.remove(video_filename)
        if os.path.exists(thumb_filename): os.remove(thumb_filename)
        
        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(f"Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hi! Send me a link. I now support THUMBNAILS!")

if __name__ == '__main__':
    # NEW: Added timeouts to the main application builder too
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(60).write_timeout(60).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_video))
    
    application.run_polling()
