import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9179945924:AAGwCM-8BFyu5d3D7Mna6xp1tGDfMbnFwqk")

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📧 Generate Temp Email", callback_data="gen_mail")],
        [InlineKeyboardButton("📥 Check Inbox", callback_data="check_inbox")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🛡️ **Welcome to the Temp Mail Bot!**\n\n"
        "No need to type complex commands anymore. "
        "Just use the buttons below to create and manage your temporary inbox instantly!"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data == "gen_mail":
        try:
            domains_res = requests.get("https://api.mail.tm/domains", timeout=10)
            if domains_res.status_code != 200:
                await query.message.reply_text("❌ Could not connect to mail server.")
                return
                
            domain = domains_res.json()['hydra:member'][0]['domain']
            
            import random
            import string
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            email = f"{username}@{domain}"
            password = "Password123!"
            
            create_res = requests.post("https://api.mail.tm/accounts", json={"address": email, "password": password}, timeout=10)
            
            if create_res.status_code in [200, 201]:
                token_res = requests.post("https://api.mail.tm/token", json={"address": email, "password": password}, timeout=10)
                token = token_res.json().get('token')
                
                user_sessions[chat_id] = {"email": email, "token": token}
                
                keyboard = [
                    [InlineKeyboardButton("📥 Check Inbox", callback_data="check_inbox")],
                    [InlineKeyboardButton("🔄 Generate New", callback_data="gen_mail")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(
                    f"✅ **Your Temporary Email:**\n`{email}`\n\nClick below to check incoming messages or OTPs!",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text("❌ Failed to create temporary email account.")
        except Exception as e:
            logger.error(f"Error generating email: {e}")
            await query.message.reply_text("❌ An error occurred while generating email.")

    elif data == "check_inbox":
        if chat_id not in user_sessions:
            keyboard = [[InlineKeyboardButton("📧 Generate Temp Email first", callback_data="gen_mail")]]
            await query.message.edit_text("⚠️ You haven't generated an email yet!", reply_markup=InlineKeyboardMarkup(keyboard))
            return
            
        session = user_sessions[chat_id]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        try:
            res = requests.get("https://api.mail.tm/messages", headers=headers, timeout=10)
            if res.status_code == 200:
                messages = res.json().get('hydra:member', [])
                if not messages:
                    keyboard = [
                        [InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_inbox")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                    ]
                    await query.message.edit_text(
                        f"📥 Inbox for `{session['email']}` is currently empty.",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown"
                    )
                else:
                    keyboard = []
                    msg_text = f"📥 **Inbox Messages:**\n\n"
                    for msg in messages:
                        msg_id = msg.get('id')
                        sender = msg.get('from', {}).get('address', 'Unknown')
                        subject = msg.get('subject', 'No Subject')
                        msg_text += f"👤 **From:** {sender}\n📌 **Subject:** {subject}\n\n"
                        keyboard.append([InlineKeyboardButton(f"📖 Read: {subject[:20]}...", callback_data=f"read_{msg_id}")])
                    
                    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="check_inbox"), InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
                    await query.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            else:
                await query.message.reply_text("❌ Failed to fetch inbox messages.")
        except Exception as e:
            logger.error(f"Error checking inbox: {e}")
            await query.message.reply_text("❌ An error occurred while checking inbox.")

    elif data.startswith("read_"):
        msg_id = data.split("_")[1]
        session = user_sessions[chat_id]
        headers = {"Authorization": f"Bearer {session['token']}"}
        
        try:
            res = requests.get(f"https://api.mail.tm/messages/{msg_id}", headers=headers, timeout=10)
            if res.status_code == 200:
                msg_data = res.json()
                sender = msg_data.get('from', {}).get('address', 'Unknown')
                subject = msg_data.get('subject', 'No Subject')
                text_body = msg_data.get('text', 'No text content available.')
                
                keyboard = [
                    [InlineKeyboardButton("📥 Back to Inbox", callback_data="check_inbox")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                await query.message.edit_text(
                    f"📩 **From:** {sender}\n📌 **Subject:** {subject}\n\n📝 **Content:**\n{text_body}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text("❌ Could not read the message.")
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            await query.message.reply_text("❌ An error occurred while reading the message.")

    elif data == "main_menu":
        await start(update, context)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🛡️ Temporary Mail Bot with Inline Buttons is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
