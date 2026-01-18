import os
import logging
import asyncio
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

# --- PART 2: BOT CONFIGURATION ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = "8503783055:AAGM5zPrqwMTnuPUwY4FStJtge0WDdB8N0I"

# GLOBAL LOCK: Queue system to prevent crashes
download_lock = asyncio.Lock()

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_first_name = update.effective_user.first_name
    
    if download_lock.locked():
        await update.message.reply_text(f"⚠️ Added to queue, {user_first_name}...\nPlease wait.")

    async with download_lock:
        status_msg = await update.message.reply_text(f"⏳ Analyzing link for {user_first_name}...")

        # NEW SETTINGS: Allow Images and Carousels (Playlists)
        ydl_opts = {
            'format': 'best',             # Get best quality (Video OR Image)
            'outtmpl': 'downloads/%(id)s.%(ext)s', # Save with correct extension (.jpg, .mp4, etc)
            'noplaylist': False,          # ALLOW downloading multiple items (Carousels)
            'writethumbnail': False,      # We don't need separate thumbnails for images
            'extract_flat': False,
        }

        try:
            loop = asyncio.get_event_loop()
            
            # 1. Extract Info and Download
            def run_yt_dlp():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)

            info = await loop.run_in_executor(None, run_yt_dlp)
            
            # 2. Handle Multiple Files (Carousel/Playlist) vs Single File
            entries = []
            if 'entries' in info:
                # It is a Carousel or Playlist
                entries = info['entries']
            else:
                # It is a Single Post
                entries = [info]

            await status_msg.edit_text(f"✅ Found {len(entries)} file(s). Uploading now...")

            # 3. Loop through all downloaded files and send them
            for entry in entries:
                # Some entries might be None if extraction failed for one item
                if not entry: continue

                file_id = entry.get('id')
                ext = entry.get('ext')
                title = entry.get('title', 'Media')
                
                # Construct the filename
                filename = f"downloads/{file_id}.{ext}"
                
                # Check if file exists before trying to send
                if os.path.exists(filename):
                    with open(filename, 'rb') as f:
                        # CHECK: Is it an Image or a Video?
                        if ext in ['jpg', 'jpeg', 'png', 'webp']:
                            await update.message.reply_photo(photo=f, caption=title[:50], read_timeout=60, write_timeout=60)
                        else:
                            await update.message.reply_video(video=f, caption=title[:50], read_timeout=60, write_timeout=60)
                    
                    # Delete after sending
                    os.remove(filename)
                else:
                    # Sometimes yt-dlp merges formats and changes extension to .mkv
                    # This is a fallback to find the file
                    for possible_ext in ['mp4', 'mkv', 'webm']:
                        alt_filename = f"downloads/{file_id}.{possible_ext}"
                        if os.path.exists(alt_filename):
                            with open(alt_filename, 'rb') as f:
                                await update.message.reply_video(video=f, caption=title[:50])
                            os.remove(alt_filename)
                            break

            await status_msg.delete()

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}\n(This might be a private post or unsupported format)")
            print(f"Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot Ready! I can now download:\n- Videos\n- Photos\n- Instagram Carousels (Multiple Slides)")

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(60).write_timeout(60).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_video))
    
    application.run_polling()
