import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from datetime import datetime, timedelta
import os

# ----------------- Configuration -----------------

GENDER, NAME, FATHER, TOPIC = range(4)

CSV_FILE = "users.csv"
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "-1002973160252"))
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # <-- Replace with your bot token
TOPICS_PER_PAGE = 10

# Short label → Full dua text
TOPIC_MAP = {
    "Faith & Taqwa": "Increase in iman (faith) and taqwa (piety).",
    "Guidance": "Guidance in difficult decisions and daily life.",
    "Worship": "Steadfastness in prayers, fasting, and worship.",
    "Love for Allah": "Love for Allah, His Messenger ﷺ, and the Qur'an.",
    "Forgiveness": "Forgiveness and protection from sins.",
    "Health": "Physical health and recovery from illness.",
    "Mental Peace": "Mental peace, patience, and relief from anxiety.",
    "Protection": "Protection from stress, depression, and harmful habits.",
    "Strength": "Strength to perform acts of worship despite difficulties.",
    "Children": "Righteousness and success for children and future generations.",
    "Marriage": "Happy, loving, and respectful marriages.",
    "Parents": "Protection and care for parents and elders.",
    "Family": "Family unity, kindness, and mutual understanding.",
    "Friendships": "Blessings in friendships and community ties.",
    "Rizq": "Halal and sufficient rizq (sustenance).",
    "Success": "Success in studies, work, or business.",
    "Debt Relief": "Protection from debt and financial hardship.",
    "Opportunities": "Opportunities for growth, prosperity, and helping others.",
    "Safety": "Safety from accidents, calamities, and harm.",
    "Evil Protection": "Protection from evil, envy, black magic, and oppression.",
    "Security": "Security in travel, home, and public life.",
    "Trials": "Strength to overcome trials and challenges.",
    "Patience": "Patience (sabr) and gratitude (shukr) in all circumstances.",
    "Character": "Humility, honesty, and good character.",
    "Avoid Negativity": "Avoiding arrogance, jealousy, and harmful behavior.",
    "Excellence": "Excellence in worship and contribution to society.",
    "Ease": "Ease in exams, work challenges, or legal matters.",
    "Healing": "Healing after loss or grief.",
    "Marriage Guidance": "Guidance in marriage or family decisions.",
    "Comfort": "Comfort for those struggling with loneliness or hardship."
}

# ----------------- Helper Functions -----------------

def load_csv():
    try:
        df = pd.read_csv(CSV_FILE, dtype={"user_id": int}, parse_dates=["timestamp"])
    except FileNotFoundError:
        df = pd.DataFrame(columns=["user_id", "Gender", "Name", "Father's Name", "Topic", "timestamp"])
        df.to_csv(CSV_FILE, index=False)
    return df

def save_csv(df):
    df.to_csv(CSV_FILE, index=False)

def build_topic_keyboard(selected_topics, page=0):
    start = page * TOPICS_PER_PAGE
    end = start + TOPICS_PER_PAGE
    topics_on_page = list(TOPIC_MAP.keys())[start:end]

    keyboard = []
    row = []

    # 2 buttons per row
    for i, short_label in enumerate(topics_on_page, start=1):
        full_text = TOPIC_MAP[short_label]
        text = f"✅ {short_label}" if full_text in selected_topics else short_label
        row.append(InlineKeyboardButton(text, callback_data=short_label))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"PAGE_{page-1}"))
    if end < len(TOPIC_MAP):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"PAGE_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    # Done button
    keyboard.append([InlineKeyboardButton("✅ Done", callback_data="DONE")])

    return InlineKeyboardMarkup(keyboard)

# ----------------- Handlers -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Sign Up", callback_data='signup')],
        [InlineKeyboardButton("Remove Entry", callback_data='remove')]
    ]
    await update.message.reply_text(
        "Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def remove_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    df = load_csv()
    if user_id in df["user_id"].values:
        df = df[df["user_id"] != user_id]
        save_csv(df)
        await query.message.reply_text("✅ Your entry for dua has been removed.")
    else:
        await query.message.reply_text("⚠️ You don't have an entry to remove.")

    return ConversationHandler.END

async def start_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Brother", callback_data='Brother')],
        [InlineKeyboardButton("Sister", callback_data='Sister')]
    ]
    await query.message.reply_text(
        "Are you a Brother or Sister?", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["Gender"] = query.data
    await query.message.reply_text("Enter your Name:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Name"] = update.message.text
    await update.message.reply_text("Enter your Father's Name:")
    return FATHER

async def get_father(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["Father's Name"] = update.message.text
    context.user_data["Topics"] = []
    await update.message.reply_text(
        "Choose Topics for Dua (click multiple, then Done):",
        reply_markup=build_topic_keyboard(context.user_data["Topics"], page=0)
    )
    return TOPIC

async def get_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Paging buttons
    if data.startswith("PAGE_"):
        page = int(data.split("_")[1])
        await query.edit_message_reply_markup(
            reply_markup=build_topic_keyboard(context.user_data["Topics"], page)
        )
        return TOPIC

    # DONE button
    if data == "DONE":
        selected_full = context.user_data.get("Topics", [])
        if not selected_full:
            await query.message.reply_text("⚠️ Please select at least one topic!")
            return TOPIC

        user_id = query.from_user.id
        context.user_data["user_id"] = user_id
        df = load_csv()

        # Remove entries older than 14 days
        if "timestamp" in df.columns:
            df = df[df["timestamp"] >= datetime.now() - timedelta(days=14)]

        # Remove old entries of this user
        df = df[df["user_id"] != user_id]

        now = datetime.now()
        father_name = context.user_data["Father's Name"]
        new_rows = []
        for topic in selected_full:
            new_rows.append({
                "user_id": user_id,
                "Gender": context.user_data["Gender"],
                "Name": context.user_data["Name"],
                "Father's Name": father_name,
                "Topic": topic,
                "timestamp": now
            })
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        save_csv(df)

        await query.message.reply_text("✅ Your information has been saved!")

        # Private message
        topics_text = "\n".join([f"• {t}" for t in selected_full])
        private_text = (
            f"Dear {context.user_data['Gender']} {context.user_data['Name']} "
            f"({father_name}), you will be included in our dua for:\n\n{topics_text}"
        )
        try:
            await context.bot.send_message(chat_id=user_id, text=private_text)
        except Exception as e:
            print(f"Failed to send private message: {e}")

        # Group message
        group_text = (
            f"Dear {context.user_data['Gender']}, you will be included in our dua for:\n\n{topics_text}"
        )
        try:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=group_text)
        except Exception as e:
            print(f"Failed to send group message: {e}")

        return ConversationHandler.END

    # Toggle topic selection
    if data in TOPIC_MAP:
        full_text = TOPIC_MAP[data]
        topics = context.user_data.get("Topics", [])
        if full_text in topics:
            topics.remove(full_text)
        else:
            topics.append(full_text)
        context.user_data["Topics"] = topics

    # Keep current page
    page = 0
    if query.message.reply_markup:
        for row in query.message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("PAGE_"):
                    page = int(btn.callback_data.split("_")[1])
                    break

    await query.edit_message_reply_markup(
        reply_markup=build_topic_keyboard(context.user_data["Topics"], page)
    )
    return TOPIC

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# ----------------- Main -----------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    signup_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_signup, pattern='^signup$')],
        states={
            GENDER: [CallbackQueryHandler(get_gender, pattern='^(Brother|Sister)$')],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FATHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_father)],
            TOPIC: [CallbackQueryHandler(get_topic, pattern='.*')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(signup_handler)
    app.add_handler(CallbackQueryHandler(remove_entry, pattern='^remove$'))

    print("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
