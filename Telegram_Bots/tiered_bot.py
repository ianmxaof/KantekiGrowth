from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, InlineQueryResultArticle, InputTextMessageContent, InputFile
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
import hashlib
import base64
import qrcode
from io import BytesIO
from tinydb import TinyDB, Query
import random
from logging.handlers import RotatingFileHandler
import sys
import atexit
import tempfile
import psutil
import httpx
import pytesseract
from PIL import Image
import subprocess
import re

# Set up rotating file logging
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
log_handler = RotatingFileHandler('bot.log', maxBytes=2*1024*1024, backupCount=3)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, handlers=[log_handler, logging.StreamHandler()])

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

def menu_nav_buttons(back_to: str):
    return [
        InlineKeyboardButton("⬅️ Back", callback_data=f"back_{back_to}"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="root")
    ]

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
        menu_nav_buttons("root"),
    ],
    "content": [
        [InlineKeyboardButton("🔓 Free Tier", callback_data="free_info")],
        [InlineKeyboardButton("💎 Premium Tier", callback_data="premium_info")],
        [InlineKeyboardButton("🛠️ Admin Tier", callback_data="admin_info")],
        menu_nav_buttons("features"),
    ],
    "help": [
        menu_nav_buttons("root"),
    ],
    "free_info": [
        menu_nav_buttons("content"),
    ],
    "premium_info": [
        menu_nav_buttons("content"),
    ],
    "admin_info": [
        menu_nav_buttons("content"),
    ],
    "upgrade": [
        [InlineKeyboardButton("🔓 Basic ($5/mo)", callback_data="summary_basic"), InlineKeyboardButton("💎 Premium ($15/mo)", callback_data="summary_premium")],
        [InlineKeyboardButton("👑 Elite ($30/mo)", callback_data="summary_elite")],
        menu_nav_buttons("root"),
    ],
    "leaderboard": [
        menu_nav_buttons("root"),
    ],
    "referral": [
        [InlineKeyboardButton("Get My Link", callback_data="refer_link")],
        menu_nav_buttons("root"),
    ],
    "promote": [
        menu_nav_buttons("root"),
    ],
    "howitworks": [
        menu_nav_buttons("root"),
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
        "For support, contact @wizardstick."
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
        "Contact @wizardstick or use /promote to submit your info."
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
        "• <b>Need help?</b> Use /help or contact @wizardstick."
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
    "Questions? Tap /menu or contact @wizardstick."
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
    elif referrer_id and referrer_id != user_id and not user.get("referrer_id"):
        set_referrer(user_id, referrer_id)
    await update.message.reply_text(
        f"Welcome, {update.effective_user.first_name}! Your tier: {user['tier']}"
    )
    await update.message.reply_text(
        MENU_TEXT["root"],
        reply_markup=InlineKeyboardMarkup(MENU_TREE["root"]),
        parse_mode=ParseMode.HTML
    )
    # Immediately show referral link after onboarding
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    public_link = "https://t.me/+UySByFBFPqA0YTcx"
    text = (
        "🔥 <b>Join the AOF VIP Group for exclusive content!</b>\n\n"
        f"<b>Public Group:</b> {public_link}\n"
        f"<b>Referral Link:</b> {referral_link}\n\n"
        "Invite your friends to join and unlock rewards!\n"
        "<b>You get credit when your referral upgrades, not just joins.</b>\n\n"
        "<i>Forward this message to your friends or share your unique referral link below.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("👥 Join Public Group", url=public_link)],
        [InlineKeyboardButton("🚀 Use Referral Link", url=referral_link)],
        [InlineKeyboardButton("🐦 Share to X/Twitter", url=f"https://twitter.com/intent/tweet?text=Join%20this%20VIP%20Telegram%20bot!%20{referral_link}")],
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
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
    logging.info(f"[CALLBACK ROUTE] button_handler: data={query.data}")
    await query.answer()
    user_id = query.from_user.id

    if query.data == "upgrade":
        logging.info("[CALLBACK ROUTE] button_handler: upgrade")
        await query.edit_message_text(
            MENU_TEXT["upgrade"],
            reply_markup=InlineKeyboardMarkup(MENU_TREE["upgrade"]),
            parse_mode=ParseMode.HTML
        )
    elif query.data.startswith("show_pay_instructions_"):
        tier = query.data.replace("show_pay_instructions_", "")
        logging.info(f"[CALLBACK ROUTE] button_handler: show_pay_instructions for tier={tier}")
        await pay(update, context, tier)
    else:
        logging.warning(f"[CALLBACK ROUTE] button_handler: Unknown action for data={query.data}")
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

def generate_user_code(user_id: int) -> str:
    # SHA256, base32, 8 chars
    h = hashlib.sha256(str(user_id).encode()).digest()
    return base64.b32encode(h)[:8].decode('utf-8')

async def pay(update: Update, context: CallbackContext, tier: str = "premium"):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    eth_address = os.getenv("ETH_WALLET_ADDRESS", "[not set]")
    tron_address = os.getenv("TRON_WALLET_ADDRESS", "[not set]")
    user_code = generate_user_code(user_id)
    tier_amounts = {"basic": 5, "premium": 15, "elite": 30}
    amount = tier_amounts.get(tier, 15)
    tron_uri = f"tron:{tron_address}?amount={amount}&message={user_code}"
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(tron_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    msg = (
        f"<b>💸 Upgrade: {tier.capitalize()} Tier Payment</b>\n\n"
        "<b>How to Pay:</b>\n"
        "1. <b>Scan the QR code below</b> with your crypto wallet app (TronLink, Trust Wallet, Binance, etc.).\n"
        f"2. <b>Confirm the payment:</b> Amount: <b>{amount} USDT</b> (TRC20), Memo/Tag: <code>{user_code}</code>\n"
        "3. <b>Or copy the address and memo below</b> and paste them into your wallet app.\n"
        "4. <b>Send the payment.</b> Your upgrade will be automatic if you use the correct memo/tag.\n"
        "5. <b>If you paid anonymously or have issues, contact @wizardstick or use /manualupgrade.</b>\n\n"
        f"<b>TRON (TRC20 USDT) Address:</b> <code>{tron_address}</code>\n"
        f"<b>Your Unique Code (memo/tag):</b> <code>{user_code}</code>\n"
    )
    keyboard = [
        [
            InlineKeyboardButton("📋 Copy Address", callback_data=f"copy_tron_address_{tier}"),
            InlineKeyboardButton("📋 Copy Memo", callback_data=f"copy_memo_{tier}")
        ]
    ]
    if update.message:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_photo(photo=bio, caption=f"Scan to pay with TRON (USDT-TRC20) for {amount} USDT")
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(keyboard))
        await context.bot.send_photo(chat_id=chat_id, photo=bio, caption=f"Scan to pay with TRON (USDT-TRC20) for {amount} USDT")

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
    logging.info(f"[CALLBACK ROUTE] nav_handler: data={query.data}")
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
    # refer_link is handled by its own handler
    if key == "refer_link":
        return
    # Handle back navigation
    if key.startswith("back_"):
        back_to = key[len("back_"):]
        if back_to in MENU_TEXT:
            await query.edit_message_text(
                MENU_TEXT[back_to],
                reply_markup=InlineKeyboardMarkup(MENU_TREE.get(back_to, [])),
                parse_mode=ParseMode.HTML
            )
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
    summary += "\n\n<i>Tip: Tap 'Pay with Wallet' for instant wallet payment instructions.</i>"
    keyboard = [[
        InlineKeyboardButton("💳 Pay with Wallet", callback_data=f"show_pay_instructions_{tier}"),
        InlineKeyboardButton("💸 Manual Payment", callback_data=f"manual_payment_{tier}")
    ]]
    if tier == "basic" and BASIC_LINK:
        keyboard.append([InlineKeyboardButton("🌐 Multi-Use Link", url=BASIC_LINK)])
    if tier == "premium" and PREMIUM_LINK:
        keyboard.append([InlineKeyboardButton("🌐 Multi-Use Link", url=PREMIUM_LINK)])
    if tier == "elite" and ELITE_LINK:
        keyboard.append([InlineKeyboardButton("🌐 Multi-Use Link", url=ELITE_LINK)])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="upgrade")])
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
        invite_link = await context.bot.create_chat_link_invite_link(
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

async def refer_link_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    public_link = "https://t.me/+UySByFBFPqA0YTcx"
    text = (
        "🔥 <b>Join the AOF VIP Group for exclusive content!</b>\n\n"
        f"<b>Public Group:</b> {public_link}\n"
        f"<b>Referral Link:</b> {referral_link}\n\n"
        "Invite your friends to join and unlock rewards!\n"
        "<b>You get credit when your referral upgrades, not just joins.</b>\n\n"
        "<i>Forward this message to your friends or share your unique referral link below.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("👥 Join Public Group", url=public_link)],
        [InlineKeyboardButton("🚀 Use Referral Link", url=referral_link)],
    ]
    await context.bot.send_message(
        chat_id=user_id,
        text=text,
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
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    text = (
        f"<b>Your Profile</b>\n\n"
        f"Referrals: <b>{total}</b>\nStreak: <b>{streak}</b> weeks\nBadges: {' '.join(badges) if badges else 'None'}\n\n"
        f"<b>Your Referral Link:</b> <code>{referral_link}</code>\n"
        "<i>Share this link. You get credit when your referral upgrades, not just joins.</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# --- Limited-Time Rewards ---
def check_and_reward_referrer(user_id: int, context: CallbackContext):
    user = get_user(user_id)
    week = datetime.date.today().isocalendar()[1]
    # Award badge for first referral
    if user and user.get("referral_count", 0) == 1:
        add_badge(user_id, "🥇 First Referral")
        context.bot.loop.create_task(context.bot.send_message(
            chat_id=user_id,
            text="🏅 Congratulations! You earned the <b>First Referral</b> badge! Keep inviting friends to unlock more rewards.",
            parse_mode=ParseMode.HTML
        ))
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
            referral_link = f"https://t.me/{bot_username}?start={user_id}"
            public_link = "https://t.me/+UySByFBFPqA0YTcx"
            text = (
                "🔥 <b>Join the AOF VIP Group for exclusive content!</b>\n\n"
                f"<b>Public Group:</b> {public_link}\n"
                f"<b>Referral Link:</b> {referral_link}\n\n"
                "Invite your friends to join and unlock rewards!\n"
                "<b>You get credit when your referral upgrades, not just joins.</b>\n\n"
                "<i>Forward this message to your friends or share your unique referral link below.</i>"
            )
            keyboard = [
                [InlineKeyboardButton("👥 Join Public Group", url=public_link)],
                [InlineKeyboardButton("🚀 Use Referral Link", url=referral_link)],
                [InlineKeyboardButton("🐦 Share to X/Twitter", url=f"https://twitter.com/intent/tweet?text=Join%20this%20VIP%20Telegram%20bot!%20{referral_link}")],
            ]
            await app.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
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
            "3. If the problem persists, contact @wizardstick."
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

# --- All-Time Leaderboard Command ---
async def alltime_leaderboard(update: Update, context: CallbackContext):
    users = all_users()
    sorted_users = sorted(users, key=lambda u: u.get("referral_count", 0), reverse=True)
    text = "🏆 <b>All-Time Referral Leaderboard</b>\n\n"
    for i, user in enumerate(sorted_users[:10], 1):
        name = f"User {user['user_id']}"
        count = user.get("referral_count", 0)
        text += f"{i}. <code>{name}</code> — <b>{count}</b> referrals\n"
    text += f"\nTotal referred members: <b>{get_total_referrals()}</b>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# --- Referral Analytics (Admin Stub) ---
async def referral_analytics(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_admin_or_owner(user_id):
        await update.message.reply_text("❌ Admins/owner only.")
        return
    total = get_total_referrals()
    users = all_users()
    top_referrer = max(users, key=lambda u: u.get("referral_count", 0), default=None)
    text = (
        f"<b>Referral Analytics</b>\n\n"
        f"Total referrals: <b>{total}</b>\n"
        f"Top referrer: <b>{top_referrer['user_id'] if top_referrer else 'N/A'}</b> ({top_referrer['referral_count'] if top_referrer else 0})\n"
        f"Users with 0 referrals: <b>{sum(1 for u in users if u.get('referral_count', 0) == 0)}</b>\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

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
TIER_SUMMARIES["basic"] += "\n\n<b>Anonymous/Manual Payment:</b>\nPay via the multi-use link or QR, then send proof and your Telegram username to @wizardstick or use /manualupgrade."
TIER_SUMMARIES["premium"] += "\n\n<b>Anonymous/Manual Payment:</b>\nPay via the multi-use link or QR, then send proof and your Telegram username to @wizardstick or use /manualupgrade."
TIER_SUMMARIES["elite"] += "\n\n<b>Anonymous/Manual Payment:</b>\nPay via the multi-use link or QR, then send proof and your Telegram username to @wizardstick or use /manualupgrade."

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
    await pay(update, context, tier)

# --- Copy Address/Memo Handler ---
async def copy_button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    eth_address = os.getenv("ETH_WALLET_ADDRESS", "[not set]")
    tron_address = os.getenv("TRON_WALLET_ADDRESS", "[not set]")
    user_code = generate_user_code(user_id)
    if query.data.startswith("copy_tron_address_"):
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"TRON (TRC20 USDT) Address:\n<code>{tron_address}</code>", parse_mode=ParseMode.HTML)
    elif query.data.startswith("copy_memo_"):
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Your Unique Code (memo/tag):\n<code>{user_code}</code>", parse_mode=ParseMode.HTML)

# --- Viral X/Twitter Marketing Messages ---
VIRAL_X_MESSAGES = [
    "Unlock exclusive NSFW content and join the viral referral race! 🚀 https://t.me/+UySByFBFPqA0YTcx",
    "Earn rewards for every friend you invite to our VIP Telegram group! 🏆 Referral link in bio.",
    "Level up your access, collect badges, and climb the leaderboard. Join now: https://t.me/+UySByFBFPqA0YTcx",
    "Share your unique referral link and get instant rewards! 💎 Only on our Telegram bot.",
    "The most viral NSFW referral system on Telegram. Compete, earn, and unlock VIP perks! 👑 https://t.me/+UySByFBFPqA0YTcx",
]

# --- Automated X/Twitter Posting Scheduler ---
def start_x_marketing_scheduler():
    post_to_x_flag = os.getenv("POST_TO_X", "false").lower() == "true"
    if not post_to_x_flag:
        logging.info("X posting is disabled (POST_TO_X is not true)")
        return None
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    if not all([api_key, api_secret, access_token, access_token_secret]):
        logging.error("Missing X (Twitter) API credentials in .env")
        return None
    logging.info("X posting scheduler is enabled and credentials loaded.")
    try:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api = tweepy.API(auth)
    except Exception as e:
        logging.error(f"Failed to initialize tweepy: {e}")
        return None
    scheduler = BackgroundScheduler()
    def post_viral_x_message():
        try:
            message = random.choice(VIRAL_X_MESSAGES)
            api.update_status(message)
            logging.info(f"Posted to X: {message}")
        except Exception as e:
            logging.error(f"Failed to post to X: {e}")
    # Schedule 5 times per day (~every 4.8 hours)
    scheduler.add_job(post_viral_x_message, 'interval', hours=4.8)
    scheduler.start()
    return scheduler

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

    LOCKFILE = os.path.join(tempfile.gettempdir(), 'tiered_bot.lock')

    def is_process_running(pid):
        try:
            p = psutil.Process(pid)
            return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        except Exception:
            return False

    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, 'r') as f:
                old_pid = int(f.read().strip())
            if is_process_running(old_pid):
                print(f"[LOCKFILE] Another instance of tiered_bot.py is already running (PID {old_pid}). Exiting.")
                sys.exit(1)
            else:
                print(f"[LOCKFILE] Stale lockfile found. Removing and continuing.")
                os.remove(LOCKFILE)
        except Exception:
            os.remove(LOCKFILE)

    with open(LOCKFILE, 'w') as f:
        f.write(str(os.getpid()))

    def cleanup_lockfile():
        if os.path.exists(LOCKFILE):
            try:
                os.remove(LOCKFILE)
            except Exception:
                pass
    atexit.register(cleanup_lockfile)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^upgrade$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^show_pay_instructions_.*$"))
    app.add_handler(CallbackQueryHandler(tier_summary_basic, pattern="^summary_basic$"))
    app.add_handler(CallbackQueryHandler(tier_summary_premium, pattern="^summary_premium$"))
    app.add_handler(CallbackQueryHandler(tier_summary_elite, pattern="^summary_elite$"))
    app.add_handler(CallbackQueryHandler(paynow_handler, pattern="^paynow_.*$"))
    app.add_handler(CallbackQueryHandler(refer_link_handler, pattern="^refer_link$"))
    app.add_handler(CallbackQueryHandler(copy_button_handler, pattern="^copy_tron_address_.*$"))
    app.add_handler(CallbackQueryHandler(copy_button_handler, pattern="^copy_memo_.*$"))
    app.add_handler(CallbackQueryHandler(manual_payment_handler, pattern="^manual_payment_.*$"))
    app.add_handler(CallbackQueryHandler(manualpay_method_handler, pattern="^manualpay_method_.*$"))
    app.add_handler(CallbackQueryHandler(promote_callback, pattern="^promote$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: leaderboard_menu_handler(u, c), pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: profile(u, c), pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(manualpay_ivepaid_handler, pattern="^manualpay_ivepaid_.*$"))
    # Register nav_handler last as the generic fallback
    app.add_handler(CallbackQueryHandler(nav_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(CommandHandler("pay_basic", pay_basic))
    app.add_handler(CommandHandler("pay_premium", pay_premium))
    app.add_handler(CommandHandler("pay_elite", pay_elite))
    app.add_handler(CallbackQueryHandler(lambda u, c: pay_basic(u, c), pattern="^pay_basic$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: pay_premium(u, c), pattern="^pay_premium$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: pay_elite(u, c), pattern="^pay_elite$"))
    app.add_handler(CommandHandler("drop", drop))
    app.add_handler(CommandHandler("promote", promote_handler))
    app.add_handler(CommandHandler("setmenuimage", setmenuimage))
    app.add_handler(CommandHandler("removemenuimage", removemenuimage))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text(MENU_TEXT["help"], parse_mode=ParseMode.HTML)))
    app.add_handler(CommandHandler("editmenu", editmenu))
    app.add_handler(CommandHandler("showmenu", showmenu))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(OWNER_ID), editmenu_receive))
    app.add_handler(CommandHandler("manualupgrade", manualupgrade))
    app.add_handler(CommandHandler("alltime_leaderboard", alltime_leaderboard))
    app.add_handler(CommandHandler("referral_analytics", referral_analytics))
    app.add_handler(CommandHandler("testxpost", testxpost))
    app.add_handler(CommandHandler("postmenu", postmenu))
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.VIDEO, payment_proof_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, txid_message_handler))

    app.add_error_handler(error_handler)

    # Add weekly reset and auto-reminder jobs
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: weekly_reset_and_announce(app), 'cron', day_of_week='mon', hour=0, minute=0)
    scheduler.add_job(lambda: context.bot.loop.create_task(send_auto_reminders(app)), 'cron', hour=12, minute=0)
    scheduler.start()
    start_marketing_scheduler(app)
    schedule_vip_drops(app)
    start_x_marketing_scheduler()

    ADMIN_COMMANDS_DB = TinyDB('admin_commands.json')
    USERS_DB = TinyDB('users.json')

    async def poll_admin_commands(app):
        while True:
            Command = Query()
            pending = ADMIN_COMMANDS_DB.search(Command.status == 'pending')
            for cmd in pending:
                user_id = cmd.get('user_id')
                if cmd['type'] == 'upgrade':
                    new_tier = cmd.get('new_tier')
                    USERS_DB.update({'tier': new_tier}, Query().user_id == user_id)
                    try:
                        await app.bot.send_message(chat_id=user_id, text=f"Your tier has been upgraded to {new_tier} by admin.")
                    except Exception as e:
                        print(f"Failed to notify user {user_id}: {e}")
                elif cmd['type'] == 'ban':
                    USERS_DB.update({'banned': True}, Query().user_id == user_id)
                    try:
                        await app.bot.send_message(chat_id=user_id, text="You have been banned by admin.")
                    except Exception as e:
                        print(f"Failed to notify user {user_id}: {e}")
                elif cmd['type'] == 'message':
                    msg = cmd.get('message')
                    try:
                        await app.bot.send_message(chat_id=user_id, text=msg)
                    except Exception as e:
                        print(f"Failed to send message to user {user_id}: {e}")
                ADMIN_COMMANDS_DB.update({'status': 'done'}, doc_ids=[cmd.doc_id])
            await asyncio.sleep(5)

    async def post_init(app):
        app.create_task(poll_admin_commands(app))

    app.post_init = post_init
    app.run_polling()

async def testxpost(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    if not all([api_key, api_secret, access_token, access_token_secret]):
        await update.message.reply_text("❌ Missing X (Twitter) API credentials in .env")
        return
    try:
        import tweepy
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api = tweepy.API(auth)
        import random
        message = random.choice(VIRAL_X_MESSAGES)
        api.update_status(message)
        await update.message.reply_text(f"✅ Posted to X:\n{message}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to post to X: {e}")

async def postmenu(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=MENU_TEXT["root"],
            reply_markup=InlineKeyboardMarkup(MENU_TREE["root"]),
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text("✅ Main menu posted to this chat.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to post menu: {e}")

async def admin_menu(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
    admin_cmds = [
        ("Post Main Menu", "/postmenu"),
        ("Test X Post", "/testxpost"),
        ("Manual Upgrade", "/manualupgrade <user_id> <tier>"),
        ("Edit Menu", "/editmenu <section>"),
        ("Show Menu", "/showmenu <section>"),
        ("Referral Analytics", "/referral_analytics"),
    ]
    cmd_list = '\n'.join(cmd for _, cmd in admin_cmds)
    keyboard = [[InlineKeyboardButton(label, switch_inline_query_current_chat=cmd)] for label, cmd in admin_cmds]
    await update.message.reply_text(
        f"<b>Admin Commands</b>\n\n<code>{cmd_list}</code>\n\nTap a button to copy the command.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def inlinequery_handler(update: Update, context: CallbackContext):
    query = update.inline_query.query.strip().lower()
    user_id = update.inline_query.from_user.id
    results = []
    # Admin-only inline commands if query is 'admin' and user is OWNER_ID
    if user_id == OWNER_ID and query.startswith('admin'):
        admin_cmds = [
            ("Post Main Menu", "/postmenu"),
            ("Test X Post", "/testxpost"),
            ("Manual Upgrade", "/manualupgrade <user_id> <tier>"),
            ("Edit Menu", "/editmenu <section>"),
            ("Show Menu", "/showmenu <section>"),
            ("Referral Analytics", "/referral_analytics"),
            ("Ping", "/ping"),
            ("Group ID", "/groupid"),
            ("Users", "/users"),
            ("Log", "/log"),
            ("Broadcast", "/broadcast <message>"),
        ]
        for label, cmd in admin_cmds:
            results.append(
                InlineQueryResultArticle(
                    id=cmd,
                    title=label,
                    input_message_content=InputTextMessageContent(cmd)
                )
            )
    else:
        # Viral referral message for everyone else
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        public_link = "https://t.me/+UySByFBFPqA0YTcx"
        text = (
            "🔥 <b>Join the AOF VIP Group for exclusive content!</b>\n\n"
            f"<b>Public Group:</b> {public_link}\n"
            f"<b>Referral Link:</b> {referral_link}\n\n"
            "Invite your friends to join and unlock rewards!\n"
            "<b>You get credit when your referral upgrades, not just joins.</b>\n\n"
            "<i>Forward this message to your friends or share your unique referral link below.</i>"
        )
        results.append(
            InlineQueryResultArticle(
                id="viral_referral",
                title="Share your viral referral link!",
                input_message_content=InputTextMessageContent(text, parse_mode="HTML")
            )
        )
    await update.inline_query.answer(results, cache_time=0)

# --- Manual Payment Menu Handler ---
async def manual_payment_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    logging.info(f"[CALLBACK ROUTE] manual_payment_handler: data={query.data}")
    await query.answer()
    user_id = query.from_user.id
    tier = query.data.replace("manual_payment_", "")
    tier_amounts = {"basic": 5, "premium": 15, "elite": 30}
    amount = tier_amounts.get(tier, 15)
    # Load all supported addresses from env
    payment_methods = []
    addresses = {}
    if os.getenv("TRON_WALLET_ADDRESS"):
        payment_methods.append(("USDT (TRC20)", "usdt_trc20"))
        addresses["usdt_trc20"] = os.getenv("TRON_WALLET_ADDRESS")
    if os.getenv("ETH_WALLET_ADDRESS"):
        payment_methods.append(("ETH (ERC20)", "eth_erc20"))
        addresses["eth_erc20"] = os.getenv("ETH_WALLET_ADDRESS")
    if os.getenv("BTC_WALLET_ADDRESS"):
        payment_methods.append(("BTC", "btc"))
        addresses["btc"] = os.getenv("BTC_WALLET_ADDRESS")
    if os.getenv("BNB_WALLET_ADDRESS"):
        payment_methods.append(("BNB (BEP20)", "bnb_bep20"))
        addresses["bnb_bep20"] = os.getenv("BNB_WALLET_ADDRESS")
    if os.getenv("MATIC_WALLET_ADDRESS"):
        payment_methods.append(("MATIC (Polygon)", "matic"))
        addresses["matic"] = os.getenv("MATIC_WALLET_ADDRESS")
    if os.getenv("USDT_ERC20_ADDRESS"):
        payment_methods.append(("USDT (ERC20)", "usdt_erc20"))
        addresses["usdt_erc20"] = os.getenv("USDT_ERC20_ADDRESS")
    if os.getenv("USDT_BEP20_ADDRESS"):
        payment_methods.append(("USDT (BEP20)", "usdt_bep20"))
        addresses["usdt_bep20"] = os.getenv("USDT_BEP20_ADDRESS")
    if not payment_methods:
        await query.edit_message_text("<i>No payment addresses configured. Contact @wizardstick.</i>", parse_mode=ParseMode.HTML)
        return
    # Build menu
    buttons = [[InlineKeyboardButton(name, callback_data=f"manualpay_method_{tier}_{code}")] for name, code in payment_methods]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"summary_{tier}")])
    msg = (
        f"<b>Manual Payment for {tier.capitalize()} Tier</b>\n\n"
        f"Select a payment method below. You will receive the address, QR code, and upload instructions."
    )
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

# --- Payment Method Handler ---
import qrcode
from io import BytesIO

async def manualpay_method_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    tier = data[2]
    method = '_'.join(data[3:])
    tier_amounts = {"basic": 5, "premium": 15, "elite": 30}
    amount = tier_amounts.get(tier, 15)
    # Map method to address and URI
    env_map = {
        "usdt_trc20": (os.getenv("TRON_WALLET_ADDRESS"), f"tron:{os.getenv('TRON_WALLET_ADDRESS')}?amount={amount}"),
        "eth_erc20": (os.getenv("ETH_WALLET_ADDRESS"), f"ethereum:{os.getenv('ETH_WALLET_ADDRESS')}?value={amount}"),
        "btc": (os.getenv("BTC_WALLET_ADDRESS"), f"bitcoin:{os.getenv('BTC_WALLET_ADDRESS')}?amount={amount}"),
        "bnb_bep20": (os.getenv("BNB_WALLET_ADDRESS"), f"bnb:{os.getenv('BNB_WALLET_ADDRESS')}?amount={amount}"),
        "matic": (os.getenv("MATIC_WALLET_ADDRESS"), f"matic:{os.getenv('MATIC_WALLET_ADDRESS')}?amount={amount}"),
        "usdt_erc20": (os.getenv("USDT_ERC20_ADDRESS"), f"ethereum:{os.getenv('USDT_ERC20_ADDRESS')}?value={amount}"),
        "usdt_bep20": (os.getenv("USDT_BEP20_ADDRESS"), f"bnb:{os.getenv('USDT_BEP20_ADDRESS')}?amount={amount}"),
    }
    address, uri = env_map.get(method, (None, None))
    if not address or address == "[not set]":
        await query.edit_message_text("<i>Payment address not configured. Contact @wizardstick.</i>", parse_mode=ParseMode.HTML)
        return
    # Generate QR code
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    msg = (
        f"<b>{method.replace('_', ' ').upper()} Payment</b>\n\n"
        f"Send <b>{amount} USDT</b> (or equivalent) to:\n<code>{address}</code>\n\n"
        "Scan the QR code below with your wallet app, or copy the address.\n\n"
        "After payment, click the button below to begin validation."
    )
    keyboard = [
        [InlineKeyboardButton("I've Paid", callback_data=f"manualpay_ivepaid_{tier}_{method}")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"manual_payment_{tier}")]
    ]
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    await context.bot.send_photo(chat_id=query.from_user.id, photo=InputFile(bio), caption=f"{method.replace('_', ' ').upper()} QR for {amount} USDT")
    # Set user_data flag for payment context
    context.user_data["manualpay_context"] = {"tier": tier, "method": method, "amount": amount}

# --- I've Paid Handler ---
async def manualpay_ivepaid_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    context.user_data['awaiting_txid'] = True
    context.user_data['awaiting_screenshot'] = False
    logging.info(f"[STATE] User {user_id} set to awaiting_txid=True")
    msg = await context.bot.send_message(
        chat_id=user_id,
        text="Step 1: <b>Right click this message → Reply</b> and enter your TXID (transaction hash).\n\nYou can find this in your wallet's transaction history after sending the payment.\n\nAfter you send your TXID, you'll be prompted to upload your payment screenshot.",
        parse_mode=ParseMode.HTML
    )
    context.user_data['awaiting_txid_message_id'] = msg.message_id

# --- Message Handler for TXID ---
async def txid_message_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    logging.info(f"[TXID HANDLER] Triggered by user {user_id}. awaiting_txid={context.user_data.get('awaiting_txid')}, expected_reply_id={context.user_data.get('awaiting_txid_message_id')}, actual_reply_id={getattr(update.message.reply_to_message, 'message_id', None)}")
    if not context.user_data.get('awaiting_txid'):
        await update.message.reply_text("Not expecting a TXID right now. Please start the payment process again.")
        logging.info(f"[TXID HANDLER] User {user_id} not in awaiting_txid state.")
        return
    expected_reply_id = context.user_data.get('awaiting_txid_message_id')
    if not update.message.reply_to_message or update.message.reply_to_message.message_id != expected_reply_id:
        await update.message.reply_text("Please reply directly to the TXID prompt message.")
        logging.info(f"[TXID HANDLER] User {user_id} did not reply to correct message. expected={expected_reply_id}, got={getattr(update.message.reply_to_message, 'message_id', None)}")
        return
    txid = update.message.text.strip()
    # Basic TXID validation (length, hex, etc.)
    if not (len(txid) >= 32 and all(c in '0123456789abcdefABCDEF' for c in txid if c.isalnum())):
        await update.message.reply_text("❌ That doesn't look like a valid TXID. Please try again.")
        logging.info(f"[TXID HANDLER] User {user_id} submitted invalid TXID: {txid}")
        return
    context.user_data['txid'] = txid
    context.user_data['awaiting_txid'] = False
    context.user_data['awaiting_screenshot'] = True
    context.user_data.pop('awaiting_txid_message_id', None)
    logging.info(f"[STATE] User {user_id} submitted TXID, now awaiting_screenshot=True")
    await update.message.reply_text(
        "Step 2: Please upload your payment screenshot (photo, document, or video).\n\nThis helps us verify your payment quickly.",
        parse_mode=ParseMode.HTML
    )

async def validate_txid(chain, txid, expected_address, expected_amount, memo=None):
    try:
        if chain == "usdt_trc20":
            # Tronscan
            url = f"https://apilist.tronscan.org/api/transaction-info?hash={txid}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
            if not data or data.get("contractRet") != "SUCCESS":
                return False, "Transaction not found or not successful."
            to_addr = data.get("toAddress", "").lower()
            amount = int(data.get("amount", 0)) / 1e6
            if to_addr != expected_address.lower():
                return False, f"Destination address mismatch: {to_addr} != {expected_address}"
            if amount < expected_amount:
                return False, f"Amount too low: {amount} < {expected_amount}"
            if memo and data.get("data", "") != memo:
                return False, "Memo/tag mismatch."
            return True, data
        elif chain == "eth_erc20":
            # Etherscan
            api_key = os.getenv("ETHERSCAN_API_KEY")
            url = f"https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}&apikey={api_key}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
            tx = data.get("result")
            if not tx:
                return False, "Transaction not found."
            to_addr = tx.get("to", "").lower()
            value = int(tx.get("value", "0x0"), 16) / 1e18
            if to_addr != expected_address.lower():
                return False, f"Destination address mismatch: {to_addr} != {expected_address}"
            if value < expected_amount:
                return False, f"Amount too low: {value} < {expected_amount}"
            return True, tx
        elif chain == "bnb_bep20":
            # BscScan
            url = f"https://api.bscscan.com/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
            tx = data.get("result")
            if not tx:
                return False, "Transaction not found."
            to_addr = tx.get("to", "").lower()
            value = int(tx.get("value", "0x0"), 16) / 1e18
            if to_addr != expected_address.lower():
                return False, f"Destination address mismatch: {to_addr} != {expected_address}"
            if value < expected_amount:
                return False, f"Amount too low: {value} < {expected_amount}"
            return True, tx
        elif chain == "matic":
            # Polygonscan
            url = f"https://api.polygonscan.com/api?module=proxy&action=eth_getTransactionByHash&txhash={txid}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
            tx = data.get("result")
            if not tx:
                return False, "Transaction not found."
            to_addr = tx.get("to", "").lower()
            value = int(tx.get("value", "0x0"), 16) / 1e18
            if to_addr != expected_address.lower():
                return False, f"Destination address mismatch: {to_addr} != {expected_address}"
            if value < expected_amount:
                return False, f"Amount too low: {value} < {expected_amount}"
            return True, tx
        elif chain == "btc":
            # Blockstream
            url = f"https://blockstream.info/api/tx/{txid}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return False, "Transaction not found."
                data = resp.json()
            vouts = data.get("vout", [])
            found = False
            for vout in vouts:
                if expected_address in vout.get("scriptpubkey_address", "") and vout.get("value", 0)/1e8 >= expected_amount:
                    found = True
                    break
            if not found:
                return False, "No matching output found."
            return True, data
        return False, "Unsupported chain."
    except Exception as e:
        return False, str(e)

def classify_payment_status(ocr_text: str):
    """
    Classifies payment status from OCR text.
    Returns (status, matched_keyword)
    """
    text = ocr_text.lower()
    keywords = [
        ("success", ["success", "completed", "confirmed", "transaction complete", "payment complete", "done", "approved"]),
        ("pending", ["pending", "processing", "in progress", "awaiting"]),
        ("failed", ["failed", "declined", "rejected", "error", "cancelled"]),
    ]
    for status, words in keywords:
        for word in words:
            if re.search(rf"\b{re.escape(word)}\b", text):
                return status, word
    return "unknown", None

# Patch payment_proof_handler to use OCR/classifier and log results
async def payment_proof_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.user_data.get('awaiting_screenshot'):
        return  # Ignore if not in screenshot state
    proof_state = context.user_data.get("manualpay_context")
    txid = context.user_data.get("txid")
    if not (proof_state and txid and context.user_data.get("awaiting_payment_proof")):
        return
    user = update.effective_user
    file_id = None
    file_type = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    else:
        await update.message.reply_text("Please upload a photo, document, or video as payment proof.")
        return
    # Download file for OCR if photo or document
    ocr_text = ""
    classifier_status = "unknown"
    matched_keyword = None
    temp_path = None
    if file_type in ("photo", "document"):
        file = await context.bot.get_file(file_id)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            temp_path = tmp.name
        await file.download_to_drive(temp_path)
        ocr_text = await extract_text_from_image(temp_path)
        classifier_status, matched_keyword = classify_payment_status(ocr_text)
        logging.info(f"[OCR] user={user.id} txid={txid} status={classifier_status} keyword={matched_keyword} ocr_text={ocr_text[:100]}")
    else:
        logging.info(f"[OCR] user={user.id} txid={txid} status=skipped (video)")
    # If status is 'success', auto-upgrade (TODO: add blockchain validation check here)
    if classifier_status == "success":
        # TODO: Validate TXID on-chain before upgrade
        # For now, just notify user and log
        logging.info(f"[PAYMENT] user={user.id} txid={txid} auto-upgrade triggered by classifier.")
        await update.message.reply_text("✅ Payment screenshot recognized as successful! Your upgrade will be processed shortly.")
        # (Insert auto-upgrade logic here)
    else:
        # Fallback/manual review
        admin_chat = "@wizardstick"
        caption = (
            f"Payment proof from user: {user.full_name} (ID: {user.id}, @{user.username})\n"
            f"Tier: {proof_state['tier']}\nMethod: {proof_state['method']}\nAmount: {proof_state['amount']} USDT\nTXID: {txid}\n"
            f"OCR status: {classifier_status} (keyword: {matched_keyword})\n"
            f"OCR text: {ocr_text[:200]}"
        )
        if file_type == "photo":
            await context.bot.send_photo(chat_id=admin_chat, photo=file_id, caption=caption)
        elif file_type == "document":
            await context.bot.send_document(chat_id=admin_chat, document=file_id, caption=caption)
        elif file_type == "video":
            await context.bot.send_video(chat_id=admin_chat, video=file_id, caption=caption)
        logging.info(f"[PAYMENT] user={user.id} txid={txid} fallback/manual review. status={classifier_status}")
        await update.message.reply_text(
            "✅ Thank you! Your TXID and payment proof have been received. @wizardstick will review and grant VIP access soon."
        )
    context.user_data.pop("manualpay_context", None)
    context.user_data.pop("txid", None)
    context.user_data.pop("awaiting_payment_proof", None)
    context.user_data['awaiting_screenshot'] = False
    logging.info(f"[STATE] User {user_id} uploaded screenshot, state reset.")

async def extract_text_from_image(file_path: str) -> str:
    try:
        # Check if tesseract is installed
        result = subprocess.run(["tesseract", "--version"], capture_output=True)
        if result.returncode != 0:
            logging.warning("Tesseract OCR is not installed or not found in PATH.")
            return ""
        text = pytesseract.image_to_string(Image.open(file_path))
        return text
    except Exception as e:
        logging.error(f"OCR extraction failed: {e}")
        return ""

# In payment_proof_handler, after receiving screenshot:
# 1. Download file to temp path
# 2. Run extract_text_from_image
# 3. Parse for TXID, amount, address
# 4. If match, auto-upgrade; else, fallback

# Example integration (inside payment_proof_handler):
# if photo or document:
#     file = await context.bot.get_file(file_id)
#     temp_path = f"/tmp/{file_id}.jpg"
#     await file.download_to_drive(temp_path)
#     ocr_text = await extract_text_from_image(temp_path)
#     # parse ocr_text for txid, amount, address
#     # ...
#     # if valid: auto-upgrade
#     # else: forward to @wizardstick

if __name__ == "__main__":
    print(f"[STARTUP] Launching canonical bot at: {os.path.abspath(__file__)}")
    main()
