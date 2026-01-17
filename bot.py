import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

# 1. SETUP LOGGING (Good for debugging your project)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. YOUR BOT TOKEN (Get this from @BotFather on Telegram)
BOT_TOKEN = "8503783055:AAGM5zPrqwMTnuPUwY4FStJtge0WDdB8N0I"

# 3. THE DOWNLOAD FUNCTION
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_first_name = update.effective_user.first_name
    
    # Notify user that processing has started
    status_msg = await update.message.reply_text(f"⏳ Processing link for {user_first_name}...\nPlease wait.")

    # Configure yt-dlp to download the file
    # We use a specific filename format to easily find it later
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Best quality
        'outtmpl': 'downloads/%(id)s.%(ext)s', # Save to 'downloads' folder
        'noplaylist': True,                    # Download single video only
    }

    try:
        # Run the download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Video')
            video_id = info.get('id')
            ext = info.get('ext')
            
            # Construct the filename
            filename = f"downloads/{video_id}.{ext}"

        # Upload to Telegram
        await update.message.reply_text(f"✅ Download complete: {video_title}\nUploading now...")
        
        with open(filename, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption=video_title)

        # CLEANUP: Delete the file from your server to save space
        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        print(e)

# 4. START COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hi! Send me a link from YouTube, Instagram, or Facebook, and I'll download it for you.")

# 5. MAIN EXECUTION
if __name__ == '__main__':
    # Create the Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add Handlers
    start_handler = CommandHandler('start', start)
    # This filter ensures the bot only reacts to text that contains 'http'
    video_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), download_video)

    application.add_handler(start_handler)
    application.add_handler(video_handler)

    # Run the bot
    print("Bot is running...")
    application.run_polling()
