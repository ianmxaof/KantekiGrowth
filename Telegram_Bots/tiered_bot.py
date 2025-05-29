from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler
from storage import (
    get_user, set_user, all_users, set_invite_sent, has_invite_sent, set_referrer, get_referrer, increment_referral_count,
    get_leaderboard, reset_weekly_referrals, add_badge, get_badges, get_total_referrals
)
import os
from dotenv import load_dotenv
from telegram.constants import ParseMode
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from telegram.ext import filters
import tweepy
import datetime
import asyncio
from typing import List, Dict
import json

# Default tier assigned on first use
DEFAULT_TIER = "free"

# Fake paywall pricing
TIERS = {
    "basic": "🔓 Basic access (limited content)",
    "premium": "💎 Premium access (full content, downloads, VIP group)",
    "elite": "👑 Elite access (all premium + early access, special badge, direct support)",
    "admin": "🛠️ Godmode"
}

SUBSCRIPTION_PRICES = {
    "basic": 500,    # 5.00 USDT
    "premium": 1500, # 15.00 USDT
    "elite": 3000    # 30.00 USDT
}

CRYPTOBOT_LINK = "https://t.me/CryptoBot?start=YOUR_BOT_ID"

# --- Inline Menu Tree ---
MENU_TREE = {
    "root": [
        [
            InlineKeyboardButton("👥 Public Group", url="https://t.me/+UySByFBFPqA0YTcx"),
            InlineKeyboardButton("🌟 Promote OF", callback_data="promote")
        ],
        [
            InlineKeyboardButton("❓ FAQ", callback_data="howitworks"),
            InlineKeyboardButton("💎 Upgrade", callback_data="upgrade")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
            InlineKeyboardButton("🔗 Referral", callback_data="referral")
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
            InlineKeyboardButton("🆘 Help", callback_data="help")
        ]
    ],
    "features": [
        [InlineKeyboardButton("📚 Content Access", callback_data="content")],
        [InlineKeyboardButton("⬅️ Back", callback_data="root")],
    ],
    "content": [
        [InlineKeyboardButton("🔓 Free Tier", callback_data="free_info")],
        [InlineKeyboardButton("💎 Premium Tier", callback_data="premium_info")],
        [InlineKeyboardButton("🛠️ Admin Tier", callback_data="admin_info")],
        [InlineKeyboardButton("⬅️ Back", callback_data="features")],
    ],
    "help": [
        [InlineKeyboardButton("⬅️ Back", callback_data="root")],
    ],
    "free_info": [
        [InlineKeyboardButton("⬅️ Back", callback_data="content")],
    ],
    "premium_info": [
        [InlineKeyboardButton("⬅️ Back", callback_data="content")],
    ],
    "admin_info": [
        [InlineKeyboardButton("⬅️ Back", callback_data="content")],
    ],
    "upgrade": [
        [InlineKeyboardButton("🔓 Basic ($5/mo)", callback_data="summary_basic"), InlineKeyboardButton("💎 Premium ($15/mo)", callback_data="summary_premium")],
        [InlineKeyboardButton("👑 Elite ($30/mo)", callback_data="summary_elite")],
        [InlineKeyboardButton("⬅️ Back", callback_data="root")],
    ],
    "leaderboard": [
        [InlineKeyboardButton("⬅️ Back", callback_data="root")],
    ],
    "referral": [
        [InlineKeyboardButton("Get My Link", callback_data="refer_link")],
        [InlineKeyboardButton("⬅️ Back", callback_data="root")],
    ],
}

MENU_TEXTS_FILE = "menu_texts.json"

# Load custom menu texts if present
try:
    with open(MENU_TEXTS_FILE, "r", encoding="utf-8") as f:
        custom_menu_texts = json.load(f)
        MENU_TEXT = {**MENU_TEXT, **custom_menu_texts}
except Exception:
    pass

MENU_TEXT = {
    "root": (
        "<b>Welcome to the Tiered Access Bot!</b>\n\n"
        "Join our public group to get started: https://t.me/+UySByFBFPqA0YTcx\n\n"
        "Choose an option below to explore features, upgrade your tier, or get help."
    ),
    "features": (
        "<b>Features Overview</b>\n\n"
        "• Access exclusive content based on your tier.\n"
        "• Upgrade for downloads, forwarding, and more.\n"
        "• Admins can broadcast and manage users.\n\n"
        "Select a feature to learn more."
    ),
    "content": (
        "<b>Content Access by Tier</b>\n\n"
        "• <b>Free:</b> Basic previews, limited access.\n"
        "• <b>Premium:</b> Full content, downloads, forwarding.\n"
        "• <b>Admin:</b> All access, user management, analytics.\n\n"
        "Tap a tier for details."
    ),
    "help": (
        "<b>Help & Info</b>\n\n"
        "This bot offers tiered access to exclusive content.\n"
        "• Use /start to register.\n"
        "• Use /pay to upgrade.\n"
        "• Use /check to see your tier.\n"
        "• Use /menu to navigate features.\n\n"
        "For support, contact @YourSupportHandle."
    ),
    "free_info": (
        "<b>Free Tier</b>\n\n"
        "You have access to our public group and basic previews.\n"
        "Join here: https://t.me/+UySByFBFPqA0YTcx\n\n"
        "Upgrade to unlock premium content and downloads."
    ),
    "premium_info": (
        "<b>Premium Tier</b>\n\n"
        "Enjoy full access, downloads, and forwarding.\n"
        "Thank you for supporting the project!"
    ),
    "admin_info": (
        "<b>Admin Tier</b>\n\n"
        "Admins can manage users, broadcast messages, and view analytics.\n"
        "Contact the owner to request admin access."
    ),
    "upgrade": (
        "<b>💎 Upgrade Your Adventure!</b>\n\n"
        "Step into the VIP zone and unlock a world of exclusive rewards, content, and status!\n\n"
        "<b>🎮 Gamified Tiers:</b>\n"
        "<b>🔓 Basic</b> — $5/mo\n"
        "• Access to public group\n"
        "• Earn badges for referrals\n"
        "• Compete on the leaderboard\n\n"
        "<b>💎 Premium</b> — $15/mo\n"
        "• All Basic perks\n"
        "• Full content drops, downloads, and VIP group access\n"
        "• Special badges, streaks, and premium-only giveaways\n"
        "• Forwarding enabled\n\n"
        "<b>👑 Elite</b> — $30/mo\n"
        "• All Premium perks\n"
        "• Early access to new drops\n"
        "• Elite badge, direct support, and secret events\n"
        "• Top of the leaderboard spotlight\n\n"
        "<b>🏆 Compete, collect, and climb the ranks!</b>\n"
        "Every referral, every upgrade, every badge brings you closer to the top.\n\n"
        "<i>Choose your destiny below and level up instantly!</i>"
    ),
    "promote": (
        "<b>Promote Your OnlyFans/Channel</b>\n\n"
        "Are you a model or creator? Get featured in our VIP group and reach thousands of fans!\n\n"
        "Contact @YourSupportHandle or use /promote to submit your info."
    ),
    "howitworks": (
        "<b>How It Works / FAQ</b>\n\n"
        "1. <b>Join</b> our public group for free previews.\n"
        "2. <b>Upgrade</b> to unlock premium content, downloads, and VIP access.\n"
        "3. <b>Refer</b> friends to earn rewards and badges.\n"
        "4. <b>Promote</b> your OnlyFans or channel to our audience.\n\n"
        "<b>FAQ:</b>\n"
        "• <b>How do I upgrade?</b> Use /pay or the menu.\n"
        "• <b>How do I get VIP access?</b> Upgrade to premium or elite.\n"
        "• <b>How do I promote my channel?</b> Use /promote or the menu.\n"
        "• <b>How do I refer friends?</b> Use /refer to get your link.\n"
        "• <b>Need help?</b> Use /help or contact @YourSupportHandle."
    ),
    "leaderboard": (
        "<b>🏆 Weekly Referral Leaderboard</b>\n\n"
        "Climb the ranks by inviting friends!\n"
        "Earn badges, streaks, and exclusive rewards.\n\n"
        "Check your position and compete for the top!\n\n"
        "Use /leaderboard to see the live board."
    ),
    "referral": (
        "<b>🔗 Referral Program</b>\n\n"
        "Invite friends with your unique link and earn rewards!\n"
        "• Every friend who upgrades boosts your rank.\n"
        "• Unlock badges, streaks, and leaderboard glory.\n\n"
        "Use /refer to get your link and share instantly!"
    ),
}

MARKETING_MESSAGE = (
    "<b>🚀 Unlock VIP Access!</b>\n\n"
    "• <b>Free:</b> Basic previews, limited features in our public group.\n"
    "• <b>Premium:</b> Full content, downloads, forwarding in our <b>VIP Channel</b>.\n"
    "• <b>Elite:</b> Early access, special badge, direct support.\n\n"
    "<b>🌟 Models & Creators:</b> Want to promote your OnlyFans or channel? Tap /promote or the menu!\n\n"
    "Join our public group: https://t.me/+UySByFBFPqA0YTcx\n"
    "Use /pay to upgrade and get your one-time VIP invite!\n"
    "Questions? Tap /menu or contact @YourSupportHandle."
)

# SUPERGROUP_ID = -1001234567890  # Replace with your supergroup's chat_id
# VIP_CHANNEL_ID = -1009876543210  # Replace with your VIP channel's chat_id
# OWNER_ID = 123456789  # Replace with your Telegram user ID

MENU_IMAGE_FILE_ID = None  # Global, replace with DB for persistence

def is_admin_or_owner(user_id):
    return user_id == OWNER_ID or (get_user(user_id) and get_user(user_id)["tier"] == "admin")

async def setmenuimage(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin_or_owner(user_id):
        await update.message.reply_text("❌ Admins/owner only.")
        return
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Send an image or GIF with this command.")
        return
    global MENU_IMAGE_FILE_ID
    MENU_IMAGE_FILE_ID = (update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id)
    await update.message.reply_text("✅ Main menu image/GIF set.")

async def removemenuimage(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin_or_owner(user_id):
        await update.message.reply_text("❌ Admins/owner only.")
        return
    global MENU_IMAGE_FILE_ID
    MENU_IMAGE_FILE_ID = None
    await update.message.reply_text("✅ Main menu image/GIF removed.")

# Start or register user
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args
    referrer_id = int(args[0]) if args and args[0].isdigit() else None

    user = get_user(user_id)
    if not user:
        set_user(user_id, DEFAULT_TIER)
        user = {"tier": DEFAULT_TIER}
        if referrer_id and referrer_id != user_id:
            set_referrer(user_id, referrer_id)
    await update.message.reply_text(
        f"Welcome, {update.effective_user.first_name}! Your tier: {user['tier']}"
    )
    await update.message.reply_text(
        MENU_TEXT["root"],
        reply_markup=InlineKeyboardMarkup(MENU_TREE["root"]),
        parse_mode=ParseMode.HTML
    )

# Check access tier
async def check(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = get_user(user_id)
    tier = user["tier"] if user else "unknown"
    await update.message.reply_text(f"Your current access tier: {tier.upper()}")

# Send tiered menu
async def menu(update: Update, context: CallbackContext):
    if MENU_IMAGE_FILE_ID:
        await update.message.reply_photo(
            photo=MENU_IMAGE_FILE_ID,
            caption=MENU_TEXT["root"],
            reply_markup=InlineKeyboardMarkup(MENU_TREE["root"]),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            MENU_TEXT["root"],
            reply_markup=InlineKeyboardMarkup(MENU_TREE["root"]),
            parse_mode=ParseMode.HTML
        )

# Handle upgrade button tap
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "upgrade":
        set_user(user_id, "premium")
        await query.edit_message_text("✅ Upgrade successful! You now have PREMIUM access.")
        await send_vip_invite(user_id, context)
    else:
        await query.edit_message_text("Unknown action.")

# Upgrade manually (admin only for now)
async def upgrade(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /upgrade <user_id> <tier>")
        return

    user = get_user(user_id)
    if not user or user["tier"] != "admin":
        await update.message.reply_text("❌ Admins only.")
        return

    target_id, new_tier = context.args
    set_user(int(target_id), new_tier)
    await update.message.reply_text(f"✅ User {target_id} upgraded to {new_tier.upper()}")

# Pay with CryptoBot
async def pay(update: Update, context: CallbackContext):
    await update.message.reply_invoice(
        title="Premium Access",
        description="Unlock full access and VIP group.",
        payload="premium_access",
        provider_token=os.getenv("CRYPTOBOT_PROVIDER_TOKEN"),
        currency="USDT",  # or BTC, ETH, etc.
        prices=[LabeledPrice("Premium Access", 1000)],  # 1000 = 10.00 USDT
        start_parameter="premium-access"
    )

# Search command
async def search(update: Update, context: CallbackContext):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /search <query>")
        return
    # Stub: search static content
    results = [f"Result for '{query}' (stub)"]
    await update.message.reply_text("\n".join(results))

# --- Inline navigation handler ---
async def nav_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    key = query.data
    # Handle tier summaries directly
    if key == "summary_basic":
        await tier_summary_basic(update, context)
        return
    if key == "summary_premium":
        await tier_summary_premium(update, context)
        return
    if key == "summary_elite":
        await tier_summary_elite(update, context)
        return
    if key not in MENU_TEXT:
        await query.edit_message_text("Unknown menu option.")
        return
    # If main menu, send image if set
    if key == "root" and MENU_IMAGE_FILE_ID:
        await query.message.reply_photo(
            photo=MENU_IMAGE_FILE_ID,
            caption=MENU_TEXT[key],
            reply_markup=InlineKeyboardMarkup(MENU_TREE.get(key, [])),
            parse_mode=ParseMode.HTML
        )
        await query.message.delete()
        return
    await query.edit_message_text(
        MENU_TEXT[key],
        reply_markup=InlineKeyboardMarkup(MENU_TREE.get(key, [])),
        parse_mode=ParseMode.HTML
    )

async def send_vip_invite(user_id: int, context: CallbackContext):
    if has_invite_sent(user_id):
        return
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=VIP_CHANNEL_ID,
            member_limit=1,
            creates_join_request=False
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Welcome to VIP! Here is your one-time invite: {invite_link.invite_link}"
        )
        set_invite_sent(user_id)
    except Exception as e:
        logging.error(f"Failed to send VIP invite: {e}")

async def getid(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # Only allow owner or admin
    user = get_user(user_id)
    if user_id != OWNER_ID and (not user or user["tier"] != "admin"):
        await update.message.reply_text("❌ Only the owner or admins can use this command.")
        return
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID: <code>{chat.id}</code>\nTitle: {chat.title}", parse_mode=ParseMode.HTML)

async def log_chat_id(update: Update, context: CallbackContext):
    chat = update.effective_chat
    print(f"Chat ID: {chat.id}, Title: {chat.title}")

def post_to_x(message: str):
    post_to_x_flag = os.getenv("POST_TO_X", "false").lower() == "true"
    if not post_to_x_flag:
        return
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("X_BEARER_TOKEN")
    if not all([api_key, api_secret, access_token, access_token_secret]):
        logging.error("Missing X (Twitter) API credentials in .env")
        return
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api = tweepy.API(auth)
        api.update_status(message)
        logging.info("Posted marketing message to X (Twitter)")
    except Exception as e:
        logging.error(f"Failed to post to X (Twitter): {e}")

# Post the inline menu to the group
async def post_menu_to_group(app):
    try:
        await app.bot.send_message(
            chat_id=SUPERGROUP_ID,
            text=MENU_TEXT["root"],
            reply_markup=InlineKeyboardMarkup(MENU_TREE["root"]),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.error(f"Failed to post menu: {e}")

def start_marketing_scheduler(app):
    scheduler = BackgroundScheduler()
    def post_marketing():
        try:
            # Post marketing message to Telegram group
            app.bot.send_message(
                chat_id=SUPERGROUP_ID,
                text=MARKETING_MESSAGE,
                parse_mode=ParseMode.HTML
            )
            # Post inline menu to Telegram group
            import asyncio
            asyncio.run(post_menu_to_group(app))
            # Post to X (Twitter)
            post_to_x(MARKETING_MESSAGE)
        except Exception as e:
            logging.error(f"Failed to post marketing message: {e}")
    scheduler.add_job(post_marketing, 'interval', hours=4.8)  # 5x daily
    scheduler.start()
    return scheduler

async def error_handler(update, context):
    print(f"Exception: {context.error}")

async def precheckout_callback(update: Update, context: CallbackContext):
    await update.pre_checkout_query.answer(ok=True)

# --- Multi-use invoice links and QR codes from .env ---
BASIC_LINK = os.getenv("CRYPTOBOT_BASIC_LINK")
BASIC_QR = os.getenv("CRYPTOBOT_BASIC_QR")
PREMIUM_LINK = os.getenv("CRYPTOBOT_PREMIUM_LINK")
PREMIUM_QR = os.getenv("CRYPTOBOT_PREMIUM_QR")
ELITE_LINK = os.getenv("CRYPTOBOT_ELITE_LINK")
ELITE_QR = os.getenv("CRYPTOBOT_ELITE_QR")

# --- Tier Summary Handlers (patched) ---
async def tier_summary_handler(update: Update, context: CallbackContext, tier: str):
    summary = TIER_SUMMARIES[tier]
    # Automated payment button
    keyboard = [[InlineKeyboardButton("💸 Pay with CryptoBot (Auto)", callback_data=f"paynow_{tier}")]]
    # Static link and QR code
    if tier == "basic" and BASIC_LINK:
        keyboard.append([InlineKeyboardButton("🌐 Multi-Use Link", url=BASIC_LINK)])
    if tier == "premium" and PREMIUM_LINK:
        keyboard.append([InlineKeyboardButton("🌐 Multi-Use Link", url=PREMIUM_LINK)])
    if tier == "elite" and ELITE_LINK:
        keyboard.append([InlineKeyboardButton("🌐 Multi-Use Link", url=ELITE_LINK)])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="upgrade")])
    # Edit message with QR code if available
    qr_url = None
    if tier == "basic" and BASIC_QR:
        qr_url = BASIC_QR
    if tier == "premium" and PREMIUM_QR:
        qr_url = PREMIUM_QR
    if tier == "elite" and ELITE_QR:
        qr_url = ELITE_QR
    if update.callback_query:
        if qr_url:
            await update.callback_query.edit_message_text(
                summary + "\n\n<b>Or scan QR to pay:</b>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            await context.bot.send_photo(
                chat_id=update.callback_query.from_user.id,
                photo=qr_url,
                caption=f"Scan to pay for {tier.capitalize()} tier. After payment, use /manualupgrade if you paid anonymously or via static link.",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.callback_query.edit_message_text(
                summary,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
    else:
        await update.message.reply_text(
            summary,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

# --- Manual Upgrade Command for Admins ---
async def manualupgrade(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /manualupgrade <user_id> <tier>")
        return
    target_id, new_tier = context.args
    set_user(int(target_id), new_tier)
    await update.message.reply_text(f"✅ User {target_id} manually upgraded to {new_tier.upper()}")
    # Send one-time VIP invite
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=VIP_CHANNEL_ID,
            member_limit=1,
            creates_join_request=False
        )
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"🎉 Welcome to VIP! Here is your one-time invite: {invite_link.invite_link}"
        )
    except Exception as e:
        logging.error(f"Failed to send VIP invite: {e}")

# Patch successful_payment_callback to always send one-time VIP invite
async def successful_payment_callback(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    set_user(user_id, "premium")
    referrer_id = get_referrer(user_id)
    if referrer_id:
        increment_referral_count(referrer_id)
        add_badge(referrer_id, "🥇 First Referral")
        check_and_reward_referrer(referrer_id, context)
        maybe_public_thank_you(referrer_id, context)
        await context.bot.send_message(
            chat_id=referrer_id,
            text="🎉 Someone you referred just upgraded! Thank you for spreading the word."
        )
    # Always send one-time VIP invite
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=VIP_CHANNEL_ID,
            member_limit=1,
            creates_join_request=False
        )
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Payment received! You are now premium. Here is your one-time VIP invite: {invite_link.invite_link}"
        )
    except Exception as e:
        logging.error(f"Failed to send VIP invite: {e}")

# --- Forwardable Full Menu ---
def get_forwardable_menu_text():
    return (
        "<b>🚀 AOF VIP Bot Menu</b>\n\n"
        "👥 <b>Join Public Group:</b> https://t.me/+UySByFBFPqA0YTcx\n"
        "💎 <b>Upgrade:</b> Use /pay or the menu to unlock premium features.\n"
        "🏆 <b>Referral Leaderboard:</b> /leaderboard\n"
        "👤 <b>Profile:</b> /profile\n"
        "🌟 <b>Promote Your Channel:</b> /promote\n"
        "❓ <b>How it Works / FAQ:</b> /menu or the menu button\n"
        "🆘 <b>Help & Commands:</b> /help\n\n"
        "Share this menu with friends to invite them!"
    )

async def refer_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    public_link = "https://t.me/+UySByFBFPqA0YTcx"
    # VIP link logic (if user is premium/elite)
    user = get_user(user_id)
    vip_link = None
    if user and user["tier"] in ("premium", "elite"):
        vip_link = os.getenv("VIP_GROUP_LINK") or "<VIP group link here>"
    # Forwardable full menu
    await update.message.reply_text(
        get_forwardable_menu_text(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    # Referral invitation message
    text = (
        "🔥 <b>Join the AOF VIP Group for exclusive content!</b>\n\n"
        f"<b>Public Group:</b> {public_link}\n"
        + (f"<b>VIP Group:</b> {vip_link}\n" if vip_link else "") +
        f"<b>Referral Link:</b> {link}\n\n"
        "Invite your friends to join and unlock rewards!\n\n"
        "<i>Forward this message to your friends or share your unique referral link below.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("👥 Join Public Group", url=public_link)],
        [InlineKeyboardButton("🚀 Use Referral Link", url=link)],
    ]
    if vip_link:
        keyboard.append([InlineKeyboardButton("💎 Join VIP Group", url=vip_link)])
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

# --- Leaderboard Command ---
async def leaderboard(update: Update, context: CallbackContext):
    board = get_leaderboard()
    text = "🏆 <b>Weekly Referral Leaderboard</b>\n\n"
    for i, user in enumerate(board, 1):
        name = f"User {user['user_id']}"
        count = user.get("weekly_referrals", 0)
        text += f"{i}. <code>{name}</code> — <b>{count}</b> referrals\n"
    text += f"\nTotal referred members: <b>{get_total_referrals()}</b>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# --- Profile Command ---
async def profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = get_user(user_id)
    badges = get_badges(user_id)
    streak = user.get("streak", 0) if user else 0
    total = user.get("referral_count", 0) if user else 0
    text = f"<b>Your Profile</b>\n\nReferrals: <b>{total}</b>\nStreak: <b>{streak}</b> weeks\nBadges: {' '.join(badges) if badges else 'None'}"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# --- Limited-Time Rewards ---
def check_and_reward_referrer(user_id: int, context: CallbackContext):
    user = get_user(user_id)
    week = datetime.date.today().isocalendar()[1]
    if user and user.get("weekly_referrals", 0) >= 3 and user.get("last_rewarded_week", 0) != week:
        # Extend premium by 1 month (simulate by setting tier)
        set_user(user_id, "premium")
        add_badge(user_id, "🏅 3+ Referrals in a Week")
        db = context.bot_data.get('db')
        if db is not None:
            db.update({"last_rewarded_week": week}, User.user_id == user_id)
        context.bot.loop.create_task(context.bot.send_message(
            chat_id=user_id,
            text="🎉 You referred 3+ friends this week! 1 month of premium unlocked."
        ))

# --- Public Thank You ---
def maybe_public_thank_you(user_id: int, context: CallbackContext):
    user = get_user(user_id)
    milestones = [5, 10, 25, 50]
    total = user.get("referral_count", 0) if user else 0
    if total in milestones:
        context.bot.loop.create_task(context.bot.send_message(
            chat_id=SUPERGROUP_ID,
            text=f"🎉 <b>User {user_id}</b> just hit <b>{total}</b> referrals! Thank you for spreading the word!",
            parse_mode=ParseMode.HTML
        ))

# --- Auto-Reminder Job ---
async def send_auto_reminders(app):
    for user in all_users():
        if user.get("referral_count", 0) == 0:
            user_id = user["user_id"]
            bot_username = (await app.bot.get_me()).username
            link = f"https://t.me/{bot_username}?start={user_id}"
            await app.bot.send_message(
                chat_id=user_id,
                text=f"Don't forget to invite friends! Here is your referral link:\n{link}"
            )

# --- Weekly Reset & Race Announcement ---
def weekly_reset_and_announce(app):
    reset_weekly_referrals()
    board = get_leaderboard()
    text = "🏁 <b>New Weekly Referral Race!</b>\n\nInvite friends to win rewards. Current leaders:\n"
    for i, user in enumerate(board, 1):
        name = f"User {user['user_id']}"
        count = user.get("weekly_referrals", 0)
        text += f"{i}. <code>{name}</code> — <b>{count}</b> referrals\n"
    text += "\nThe race resets every Monday!"
    app.bot.send_message(chat_id=SUPERGROUP_ID, text=text, parse_mode=ParseMode.HTML)

# --- Payment Handlers for Each Tier ---
async def pay_tier(update: Update, context: CallbackContext, tier: str):
    provider_token = os.getenv("CRYPTOBOT_PROVIDER_TOKEN")
    title = f"{tier.capitalize()} Subscription"
    description = f"Unlock {TIERS[tier]}"
    payload = f"{tier}_subscription"
    currency = "USDT"
    price = SUBSCRIPTION_PRICES[tier]
    prices = [LabeledPrice(f"{tier.capitalize()} Subscription", price)]
    start_parameter = f"{tier}-subscription"

    try:
        if update.callback_query:
            user_id = update.callback_query.from_user.id
            await context.bot.send_invoice(
                chat_id=user_id,
                title=title,
                description=description,
                payload=payload,
                provider_token=provider_token,
                currency=currency,
                prices=prices,
                start_parameter=start_parameter
            )
            await update.callback_query.edit_message_text(
                "💸 Check your private chat for the payment invoice!",
                parse_mode=ParseMode.HTML
            )
        elif update.message:
            await update.message.reply_invoice(
                title=title,
                description=description,
                payload=payload,
                provider_token=provider_token,
                currency=currency,
                prices=prices,
                start_parameter=start_parameter
            )
    except Exception as e:
        logging.error(f"Failed to send invoice: {e}")
        error_msg = (
            "❌ <b>Could not send payment invoice.</b>\n\n"
            "Possible reasons:\n"
            "• You must <b>start the bot in private chat</b> first.\n"
            "• Payment provider is not configured.\n"
            "• Telegram API error.\n\n"
            "<b>How to fix:</b>\n"
            "1. Tap the bot's profile and click 'Start' in private.\n"
            "2. Try again from the menu.\n"
            "3. If the problem persists, contact @YourSupportHandle."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg, parse_mode=ParseMode.HTML)
        elif update.message:
            await update.message.reply_text(error_msg, parse_mode=ParseMode.HTML)

async def pay_basic(update: Update, context: CallbackContext):
    await pay_tier(update, context, "basic")

async def pay_premium(update: Update, context: CallbackContext):
    await pay_tier(update, context, "premium")

async def pay_elite(update: Update, context: CallbackContext):
    await pay_tier(update, context, "elite")

CONTENT_DROPS = []  # In-memory queue; replace with DB for production

async def drop(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user or user["tier"] != "admin":
        await update.message.reply_text("❌ Admins only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /drop <tag> <content/link>")
        return
    tag = context.args[0]
    content = " ".join(context.args[1:])
    # Support media (if any)
    media = update.message.document or update.message.photo or update.message.video
    drop_entry = {
        "tag": tag,
        "content": content,
        "media": media.file_id if media else None,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "posted": False
    }
    CONTENT_DROPS.append(drop_entry)
    # Send to all premium/elite users
    for u in all_users():
        if u["tier"] in ("premium", "elite"):
            try:
                if media:
                    await context.bot.send_document(u["user_id"], media.file_id, caption=f"[{tag}] {content}")
                else:
                    await context.bot.send_message(u["user_id"], f"[{tag}] {content}")
            except Exception as e:
                logging.error(f"Failed to send drop to {u['user_id']}: {e}")
    await update.message.reply_text("✅ Content drop sent to premium/elite users.")

def schedule_vip_drops(app):
    async def post_due_drops():
        now = datetime.datetime.utcnow()
        for drop in CONTENT_DROPS:
            if not drop["posted"]:
                drop_time = datetime.datetime.fromisoformat(drop["timestamp"]) + datetime.timedelta(days=7)
                if now >= drop_time:
                    try:
                        if drop["media"]:
                            await app.bot.send_document(VIP_CHANNEL_ID, drop["media"], caption=f"[{drop['tag']}] {drop['content']}")
                        else:
                            await app.bot.send_message(VIP_CHANNEL_ID, f"[{drop['tag']}] {drop['content']}")
                        drop["posted"] = True
                    except Exception as e:
                        logging.error(f"Failed to post drop to VIP: {e}")
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run(post_due_drops()), 'interval', hours=1)
    scheduler.start()
    return scheduler

async def promote_handler(update: Update, context: CallbackContext):
    await update.message.reply_text(
        MENU_TEXT["promote"],
        parse_mode=ParseMode.HTML
    )

async def promote_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        MENU_TEXT["promote"],
        parse_mode=ParseMode.HTML
    )

async def editmenu(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin_or_owner(user_id):
        await update.message.reply_text("❌ Admins/owner only.")
        return
    if not context.args:
        await update.message.reply_text(f"Usage: /editmenu <section>\nAvailable: {', '.join(MENU_TEXT.keys())}")
        return
    section = context.args[0]
    if section not in MENU_TEXT:
        await update.message.reply_text(f"Section '{section}' not found. Available: {', '.join(MENU_TEXT.keys())}")
        return
    await update.message.reply_text(f"Send the new text for section <b>{section}</b> (HTML supported):", parse_mode=ParseMode.HTML)
    context.user_data['editmenu_section'] = section

async def editmenu_receive(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin_or_owner(user_id):
        return
    section = context.user_data.get('editmenu_section')
    if not section:
        return
    new_text = update.message.text
    MENU_TEXT[section] = new_text
    # Persist to file
    try:
        with open(MENU_TEXTS_FILE, "w", encoding="utf-8") as f:
            json.dump(MENU_TEXT, f, ensure_ascii=False, indent=2)
    except Exception as e:
        await update.message.reply_text(f"Error saving: {e}")
        return
    await update.message.reply_text(f"✅ Updated section <b>{section}</b>.", parse_mode=ParseMode.HTML)
    context.user_data.pop('editmenu_section', None)

async def showmenu(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin_or_owner(user_id):
        await update.message.reply_text("❌ Admins/owner only.")
        return
    if not context.args:
        await update.message.reply_text(f"Usage: /showmenu <section>\nAvailable: {', '.join(MENU_TEXT.keys())}")
        return
    section = context.args[0]
    if section not in MENU_TEXT:
        await update.message.reply_text(f"Section '{section}' not found. Available: {', '.join(MENU_TEXT.keys())}")
        return
    await update.message.reply_text(MENU_TEXT[section], parse_mode=ParseMode.HTML)

# --- Referral Link Handler (button in referral section) ---
async def refer_link_handler(update: Update, context: CallbackContext):
    await refer_handler(update, context)

# --- Leaderboard Handler (button in leaderboard section) ---
async def leaderboard_menu_handler(update: Update, context: CallbackContext):
    await leaderboard(update, context)

# --- Update main() handlers ---
# app.add_handler(CallbackQueryHandler(leaderboard_menu_handler, pattern="^leaderboard$"))
# app.add_handler(CallbackQueryHandler(refer_link_handler, pattern="^refer_link$"))
# app.add_handler(CallbackQueryHandler(lambda u, c: nav_handler(u, c), pattern="^referral$"))
# app.add_handler(CallbackQueryHandler(lambda u, c: nav_handler(u, c), pattern="^help$"))
# app.add_handler(CallbackQueryHandler(lambda u, c: nav_handler(u, c), pattern="^profile$"))
# app.add_handler(CallbackQueryHandler(lambda u, c: nav_handler(u, c), pattern="^howitworks$"))
# app.add_handler(CallbackQueryHandler(lambda u, c: nav_handler(u, c), pattern="^upgrade$"))
# app.add_handler(CallbackQueryHandler(lambda u, c: nav_handler(u, c), pattern="^promote$"))

# --- Tier Summary Messages ---
TIER_SUMMARIES = {
    "basic": (
        "<b>🔓 Basic Tier</b>\n\n"
        "• Access to public group\n"
        "• Earn badges for referrals\n"
        "• Compete on the leaderboard\n\n"
        "<b>Price:</b> $5/month\n"
        "<b>Pay with CryptoBot</b> (USDT, BTC, ETH, TON, TRX, more)\n\n"
        "Ready to unlock your journey?"
    ),
    "premium": (
        "<b>💎 Premium Tier</b>\n\n"
        "• All Basic perks\n"
        "• Full content drops, downloads, and VIP group access\n"
        "• Special badges, streaks, and premium-only giveaways\n"
        "• Forwarding enabled\n\n"
        "<b>Price:</b> $15/month\n"
        "<b>Pay with CryptoBot</b> (USDT, BTC, ETH, TON, TRX, more)\n\n"
        "Level up and join the VIPs!"
    ),
    "elite": (
        "<b>👑 Elite Tier</b>\n\n"
        "• All Premium perks\n"
        "• Early access to new drops\n"
        "• Elite badge, direct support, and secret events\n"
        "• Top of the leaderboard spotlight\n\n"
        "<b>Price:</b> $30/month\n"
        "<b>Pay with CryptoBot</b> (USDT, BTC, ETH, TON, TRX, more)\n\n"
        "Become a legend!"
    ),
}
TIER_SUMMARIES["basic"] += "\n\n<b>Anonymous/Manual Payment:</b>\nPay via the multi-use link or QR, then send proof and your Telegram username to @YourSupportHandle or use /manualupgrade."
TIER_SUMMARIES["premium"] += "\n\n<b>Anonymous/Manual Payment:</b>\nPay via the multi-use link or QR, then send proof and your Telegram username to @YourSupportHandle or use /manualupgrade."
TIER_SUMMARIES["elite"] += "\n\n<b>Anonymous/Manual Payment:</b>\nPay via the multi-use link or QR, then send proof and your Telegram username to @YourSupportHandle or use /manualupgrade."

# --- Tier Summary Handlers ---
async def tier_summary_basic(update: Update, context: CallbackContext):
    await tier_summary_handler(update, context, "basic")
async def tier_summary_premium(update: Update, context: CallbackContext):
    await tier_summary_handler(update, context, "premium")
async def tier_summary_elite(update: Update, context: CallbackContext):
    await tier_summary_handler(update, context, "elite")

# --- Pay Now Handlers ---
async def paynow_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    tier = query.data.replace("paynow_", "")
    provider_token = os.getenv("CRYPTOBOT_PROVIDER_TOKEN")
    if not provider_token:
        await query.edit_message_text("❌ Payment is currently unavailable. Please contact support.")
        return
    await query.answer()
    await pay_tier(update, context, tier)

# Main bot startup
def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env file")
    # Fetch IDs from .env
    supergroup_id = int(os.getenv("SUPERGROUP_ID"))
    vip_channel_id = int(os.getenv("VIP_CHANNEL_ID"))
    owner_id = int(os.getenv("OWNER_ID"))
    # Make these available globally
    global SUPERGROUP_ID, VIP_CHANNEL_ID, OWNER_ID
    SUPERGROUP_ID = supergroup_id
    VIP_CHANNEL_ID = vip_channel_id
    OWNER_ID = owner_id

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CallbackQueryHandler(tier_summary_basic, pattern="^summary_basic$"))
    app.add_handler(CallbackQueryHandler(tier_summary_premium, pattern="^summary_premium$"))
    app.add_handler(CallbackQueryHandler(tier_summary_elite, pattern="^summary_elite$"))
    app.add_handler(CallbackQueryHandler(paynow_handler, pattern="^paynow_.*$"))
    app.add_handler(CallbackQueryHandler(nav_handler))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^upgrade$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(CommandHandler("refer", refer_handler))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("pay_basic", pay_basic))
    app.add_handler(CommandHandler("pay_premium", pay_premium))
    app.add_handler(CommandHandler("pay_elite", pay_elite))
    app.add_handler(CallbackQueryHandler(lambda u, c: pay_basic(u, c), pattern="^pay_basic$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: pay_premium(u, c), pattern="^pay_premium$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: pay_elite(u, c), pattern="^pay_elite$"))
    app.add_handler(CommandHandler("drop", drop))
    app.add_handler(CommandHandler("promote", promote_handler))
    app.add_handler(CallbackQueryHandler(promote_callback, pattern="^promote$"))
    app.add_handler(CommandHandler("setmenuimage", setmenuimage))
    app.add_handler(CommandHandler("removemenuimage", removemenuimage))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text(MENU_TEXT["help"], parse_mode=ParseMode.HTML)))
    app.add_handler(CallbackQueryHandler(lambda u, c: leaderboard_menu_handler(u, c), pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: profile(u, c), pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: refer_link_handler(u, c), pattern="^refer_link$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: promote_callback(u, c), pattern="^promote$"))
    app.add_handler(CommandHandler("editmenu", editmenu))
    app.add_handler(CommandHandler("showmenu", showmenu))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(OWNER_ID), editmenu_receive))
    app.add_handler(CommandHandler("manualupgrade", manualupgrade))

    app.add_error_handler(error_handler)

    # Add weekly reset and auto-reminder jobs
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: weekly_reset_and_announce(app), 'cron', day_of_week='mon', hour=0, minute=0)
    scheduler.add_job(lambda: context.bot.loop.create_task(send_auto_reminders(app)), 'cron', hour=12, minute=0)
    scheduler.start()
    start_marketing_scheduler(app)
    schedule_vip_drops(app)
    app.run_polling()

if __name__ == "__main__":
    main()
