import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9179945924:AAGwCM-8BFyu5d3D7Mna6xp1tGDfMbnFwqk")

user_sessions = {}

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
        # Mail.tm API ka use karke domain list lete hain aur naya account banate hain
        domains_res = requests.get("https://api.mail.tm/domains", timeout=10)
        if domains_res.status_code != 200:
            await update.message.reply_text("❌ Could not connect to mail server.")
            return
            
        domain = domains_res.json()['hydra:member'][0]['domain']
        
        # Random email credentials generate karna
        import random
        import string
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = f"{username}@{domain}"
        password = "Password123!"
        
        # Account create karna
        create_res = requests.post("https://api.mail.tm/accounts", json={"address": email, "password": password}, timeout=10)
        
        if create_res.status_code in [200, 201]:
            # Token generate karna inbox check karne ke liye
            token_res = requests.post("https://api.mail.tm/token", json={"address": email, "password": password}, timeout=10)
            token = token_res.json().get('token')
            
            user_sessions[chat_id] = {"email": email, "token": token}
            await update.message.reply_text(f"✅ **Your Temporary Email:**\n`{email}`\n\nUse `/check` once you receive any mail or OTP!")
        else:
            await update.message.reply_text("❌ Failed to create temporary email account.")
    except Exception as e:
        logger.error(f"Error generating email: {e}")
        await update.message.reply_text("❌ An error occurred while generating email.")

async def check_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_sessions:
        await update.message.reply_text("⚠️ Please use `/gen` first to generate an email address!")
        return
        
    session = user_sessions[chat_id]
    headers = {"Authorization": f"Bearer {session['token']}"}
    
    try:
        res = requests.get("https://api.mail.tm/messages", headers=headers, timeout=10)
        if res.status_code == 200:
            messages = res.json().get('hydra:member', [])
            if not messages:
                await update.message.reply_text(f"📥 Inbox for `{session['email']}` is currently empty.")
            else:
                msg_text = f"📥 **Inbox Messages:**\n\n"
                for msg in messages:
                    msg_id = msg.get('id')
                    sender = msg.get('from', {}).get('address', 'Unknown')
                    subject = msg.get('subject', 'No Subject')
                    msg_text += f"🔹 **ID:** `{msg_id}`\n👤 **From:** {sender}\n📌 **Subject:** {subject}\n👉 `/read {msg_id}`\n\n"
                await update.message.reply_text(msg_text)
        else:
            await update.message.reply_text("❌ Failed to fetch inbox messages.")
    except Exception as e:
        logger.error(f"Error checking inbox: {e}")
        await update.message.reply_text("❌ An error occurred while checking inbox.")

async def read_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_sessions or not context.args:
        await update.message.reply_text("⚠️ Correct usage format: `/read <message_id>`")
        return
        
    msg_id = context.args[0]
    session = user_sessions[chat_id]
    headers = {"Authorization": f"Bearer {session['token']}"}
    
    try:
        res = requests.get(f"https://api.mail.tm/messages/{msg_id}", headers=headers, timeout=10)
        if res.status_code == 200:
            msg_data = res.json()
            sender = msg_data.get('from', {}).get('address', 'Unknown')
            subject = msg_data.get('subject', 'No Subject')
            text_body = msg_data.get('text', 'No text content available.')
            await update.message.reply_text(f"📩 **From:** {sender}\n📌 **Subject:** {subject}\n\n📝 **Content:**\n{text_body}")
        else:
            await update.message.reply_text("❌ Could not read the message.")
    except Exception as e:
        logger.error(f"Error reading message: {e}")
        await update.message.reply_text("❌ An error occurred while reading the message.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gen", generate_email))
    app.add_handler(CommandHandler("check", check_inbox))
    app.add_handler(CommandHandler("read", read_message))
    
    logger.info("🛡️ Temporary Mail Bot is starting polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
