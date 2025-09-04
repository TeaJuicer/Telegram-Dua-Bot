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
GROUP_CHAT_ID = -1002973160252  # Replace with your actual group chat ID
BOT_TOKEN = os.getenv("BOT_TOKEN")  # safer than hardcoding

TOPICS_PER_PAGE = 10

TOPIC_BUTTONS = [
    "Increase in iman (faith) and taqwa (piety).",
    "Guidance in difficult decisions and daily life.",
    "Steadfastness in prayers, fasting, and worship.",
    "Love for Allah, His Messenger ﷺ, and the Qur'an.",
    "Forgiveness and protection from sins.",
    "Physical health and recovery from illness.",
    "Mental peace, patience, and relief from anxiety.",
    "Protection from stress, depression, and harmful habits.",
    "Strength to perform acts of worship despite difficulties.",
    "Righteousness and success for children and future generations.",
    "Happy, loving, and respectful marriages.",
    "Protection and care for parents and elders.",
    "Family unity, kindness, and mutual understanding.",
    "Blessings in friendships and community ties.",
    "Halal and sufficient rizq (sustenance).",
    "Success in studies, work, or business.",
    "Protection from debt and financial hardship.",
    "Opportunities for growth, prosperity, and helping others.",
    "Safety from accidents, calamities, and harm.",
    "Protection from evil, envy, black magic, and oppression.",
    "Security in travel, home, and public life.",
    "Strength to overcome trials and challenges.",
    "Patience (sabr) and gratitude (shukr) in all circumstances.",
    "Humility, honesty, and good character.",
    "Avoiding arrogance, jealousy, and harmful behavior.",
    "Excellence in worship and contribution to society.",
    "Ease in exams, work challenges, or legal matters.",
    "Healing after loss or grief.",
    "Guidance in marriage or family decisions.",
    "Comfort for those struggling with loneliness or hardship."
]

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
    topics_on_page = TOPIC_BUTTONS[start:end]

    keyboard = []
    for topic in topics_on_page:
        text = f"✅ {topic}" if topic in selected_topics else topic
        keyboard.append([InlineKeyboardButton(text, callback_data=topic)])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"PAGE_{page-1}"))
    if end < len(TOPIC_BUTTONS):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"PAGE_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

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

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'remove':
        df = load_csv()
        if user_id in df["user_id"].values:
            df = df[df["user_id"] != user_id]
            save_csv(df)
            await query.message.reply_text("Your entry has been removed.")
        else:
            await query.message.reply_text("You don't have an entry to remove.")
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

    # Handle paging
    if data.startswith("PAGE_"):
        page = int(data.split("_")[1])
        await query.edit_message_reply_markup(
            reply_markup=build_topic_keyboard(context.user_data["Topics"], page)
        )
        return TOPIC

    if data == "DONE":
        user_id = query.from_user.id
        context.user_data["user_id"] = user_id

        df = load_csv()

        # Remove all entries older than 30 days globally
        if "timestamp" in df.columns:
            df = df[df["timestamp"] >= datetime.now() - timedelta(days=30)]

        # Remove old entries of this user
        df = df[df["user_id"] != user_id]

        # create multiple rows (one per topic) with timestamp
        new_rows = []
        now = datetime.now()
        for topic in context.user_data["Topics"]:
            new_rows.append({
                "user_id": user_id,
                "Gender": context.user_data["Gender"],
                "Name": context.user_data["Name"],
                "Father's Name": context.user_data["Father's Name"],
                "Topic": topic,
                "timestamp": now
            })

        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        save_csv(df)

        await query.message.reply_text("✅ Your information has been saved!")

        # --- Private DM to user ---
        topics_text = "\n".join([f"• {t}" for t in context.user_data["Topics"]])
        private_text = (
            f"Dear {context.user_data['Gender']} {context.user_data['Name']} "
            f"({context.user_data['Father's Name']}), you will be included in our dua for:\n\n{topics_text}"
        )
        try:
            await context.bot.send_message(chat_id=user_id, text=private_text)
        except Exception as e:
            print(f"Failed to send private message: {e}")

        # --- Group message without name ---
        group_text = (
            f"Dear {context.user_data['Gender']}, you will be included in our dua for:\n\n{topics_text}"
        )
        try:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=group_text)
        except Exception as e:
            print(f"Failed to send group message: {e}")

        return ConversationHandler.END

    # Toggle topic selection
    topics = context.user_data.get("Topics", [])
    if data in topics:
        topics.remove(data)
    else:
        topics.append(data)
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
        reply_markup=build_topic_keyboard(topics, page)
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
            TOPIC: [CallbackQuery
