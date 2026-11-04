import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters

# Your Telegram Bot Token is configured here
TELEGRAM_BOT_TOKEN = "9179945924:AAGwCM-8BFyu5d3D7Mna6xp1tGDfMbnFwqk"

user_sessions = {}
API_BASE = "https://www.1secmail.com/api/v1/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ **Welcome to the Temp Mail Bot!**\n\n"
        "**Available Commands:**\n"
        "👉 `/gen` - Generate a new temporary email address\n"
        "👉 `/check` - Check your inbox for incoming emails\n"
        "👉 `/read <message_id>` - Read the content of a specific email"
    )

async def generate_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        response = requests.get(f"{API_BASE}?action=genRandomMailbox&count=1")
        if response.status_code == 200:
            emails = response.json()
            if emails:
                full_email = emails[0]
                login, domain = full_email.split('@')
                user_sessions[chat_id] = {"email": full_email, "login": login, "domain": domain}
                await update.message.reply_text(f"✅ **Your Temporary Email:**\n`{full_email}`\n\nUse `/check` once you receive any mail or OTP!")
            else:
                await update.message.reply_text("❌ Failed to generate an email address.")
        else:
            await update.message.reply_text("❌ Could not connect to the mail API server.")
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

async def check_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_sessions:
        await update.message.reply_text("⚠️ Please use `/gen` first to generate an email address!")
        return
        
    session = user_sessions[chat_id]
    try:
        url = f"{API_BASE}?action=getMessages&login={session['login']}&domain={session['domain']}"
        response = requests.get(url)
        if response.status_code == 200:
            messages = response.json()
            if not messages:
                await update.message.reply_text(f"📥 Inbox for `{session['email']}` is currently empty.")
            else:
                msg_text = f"📥 **Inbox Messages:**\n\n"
                for msg in messages:
                    msg_text += f"🔹 **ID:** `{msg.get('id')}`\n👤 **From:** {msg.get('from')}\n📌 **Subject:** {msg.get('subject')}\n👉 `/read {msg.get('id')}`\n\n"
                await update.message.reply_text(msg_text)
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

async def read_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_sessions or not context.args:
        await update.message.reply_text("⚠️ Correct usage format: `/read <message_id>`")
        return
        
    msg_id = context.args[0]
    session = user_sessions[chat_id]
    try:
        url = f"{API_BASE}?action=readMessage&login={session['login']}&domain={session['domain']}&id={msg_id}"
        response = requests.get(url)
        if response.status_code == 200:
            msg_data = response.json()
            body = msg_data.get('textBody', 'No text content available.')
            await update.message.reply_text(f"📩 **From:** {msg_data.get('from')}\n📌 **Subject:** {msg_data.get('subject')}\n\n📝 **Content:**\n{body}")
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gen", generate_email))
    app.add_handler(CommandHandler("check", check_inbox))
    app.add_handler(CommandHandler("read", read_message))
    
    print("🛡️ Temporary Mail Bot is up and running...")
    app.run_polling()

if __name__ == '__main__':
    main()
