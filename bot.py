import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

# --- PART 1: KEEP ALIVE SERVER ---
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

# --- PART 2: BOT CONFIGURATION ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = "8503783055:AAGM5zPrqwMTnuPUwY4FStJtge0WDdB8N0I"

# GLOBAL LOCK: This ensures only 1 download happens at a time (prevents crashing)
download_lock = asyncio.Lock()

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_first_name = update.effective_user.first_name
    
    # 1. Check if bot is busy
    if download_lock.locked():
        await update.message.reply_text(f"⚠️ Server busy! Added your link to the queue, {user_first_name}...\nPlease wait.")

    # 2. Wait for the lock (Queue System)
    async with download_lock:
        status_msg = await update.message.reply_text(f"⏳ Downloading for {user_first_name}...")

        # FORCE MP4 FILENAME (Fixes the .None error)
        # We assume the ID might be part of the URL, but let yt-dlp handle it.
        # We just define that the output MUST be id.mp4
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': 'downloads/%(id)s.mp4',    # <--- FORCED .mp4 EXTENSION
            'noplaylist': True,
            'writethumbnail': True,
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}]
        }

        try:
            # Run the download
            # We run this in a separate thread so it doesn't block the bot's heartbeat
            loop = asyncio.get_event_loop()
            
            def run_yt_dlp():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return info

            info = await loop.run_in_executor(None, run_yt_dlp)
            
            video_title = info.get('title', 'Video')
            video_id = info.get('id')
            
            # Since we forced 'outtmpl' to end in .mp4, we know exactly where it is
            video_filename = f"downloads/{video_id}.mp4"
            thumb_filename = f"downloads/{video_id}.jpg"

            # 3. Upload
            await update.message.reply_text(f"✅ Download complete! Uploading...")
            
            with open(video_filename, 'rb') as video_file:
                if os.path.exists(thumb_filename):
                    with open(thumb_filename, 'rb') as thumb_file:
                        await update.message.reply_video(
                            video=video_file,
                            caption=video_title,
                            thumbnail=thumb_file,
                            write_timeout=60,
                            read_timeout=60
                        )
                else:
                    await update.message.reply_video(
                        video=video_file,
                        caption=video_title,
                        write_timeout=60,
                        read_timeout=60
                    )

            # 4. Cleanup
            if os.path.exists(video_filename): os.remove(video_filename)
            if os.path.exists(thumb_filename): os.remove(thumb_filename)
            await status_msg.delete()

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            print(f"Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is Ready! Send multiple links, I will queue them.")

if __name__ == '__main__':
    # Create the download folder if it doesn't exist
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(60).write_timeout(60).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_video))
    
    application.run_polling()
