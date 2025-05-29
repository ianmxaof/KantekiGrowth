from tinydb import TinyDB, Query
from typing import Optional, List, Dict
import datetime

db = TinyDB("users.json")
User = Query()

DEFAULT_TIER = "free"

def get_user(user_id: int) -> Optional[dict]:
    result = db.search(User.user_id == user_id)
    return result[0] if result else None

def set_user(user_id: int, tier: str):
    if db.contains(User.user_id == user_id):
        db.update({"tier": tier}, User.user_id == user_id)
    else:
        db.insert({"user_id": user_id, "tier": tier})

def all_users() -> List[Dict]:
    return db.all()

def set_invite_sent(user_id: int):
    db.update({"invite_sent": True}, User.user_id == user_id)

def has_invite_sent(user_id: int) -> bool:
    user = get_user(user_id)
    return user.get("invite_sent", False) if user else False

def set_referrer(user_id: int, referrer_id: int):
    if db.contains(User.user_id == user_id):
        db.update({"referrer_id": referrer_id}, User.user_id == user_id)
    else:
        db.insert({"user_id": user_id, "tier": DEFAULT_TIER, "referrer_id": referrer_id})

def get_referrer(user_id: int):
    user = get_user(user_id)
    return user.get("referrer_id") if user else None

def increment_referral_count(referrer_id: int):
    user = get_user(referrer_id)
    count = user.get("referral_count", 0) if user else 0
    db.update({"referral_count": count + 1}, User.user_id == referrer_id)
    # Weekly tracking
    week = datetime.date.today().isocalendar()[1]
    last_week = user.get("last_referral_week", 0) if user else 0
    weekly = user.get("weekly_referrals", 0) if user else 0
    if last_week == week:
        db.update({"weekly_referrals": weekly + 1}, User.user_id == referrer_id)
    else:
        db.update({"weekly_referrals": 1, "last_referral_week": week}, User.user_id == referrer_id)
    # Streak tracking
    streak = user.get("streak", 0) if user else 0
    last_streak_week = user.get("last_streak_week", 0) if user else 0
    if last_streak_week == week - 1:
        db.update({"streak": streak + 1, "last_streak_week": week}, User.user_id == referrer_id)
    elif last_streak_week != week:
        db.update({"streak": 1, "last_streak_week": week}, User.user_id == referrer_id)

def get_leaderboard(top_n=10):
    users = db.all()
    sorted_users = sorted(users, key=lambda u: u.get("weekly_referrals", 0), reverse=True)
    return sorted_users[:top_n]

def reset_weekly_referrals():
    week = datetime.date.today().isocalendar()[1]
    for user in db:
        db.update({"weekly_referrals": 0, "last_referral_week": week}, User.user_id == user["user_id"])

def add_badge(user_id: int, badge: str):
    user = get_user(user_id)
    badges = user.get("badges", []) if user else []
    if badge not in badges:
        badges.append(badge)
        db.update({"badges": badges}, User.user_id == user_id)

def get_badges(user_id: int) -> List[str]:
    user = get_user(user_id)
    return user.get("badges", []) if user else []

def get_total_referrals() -> int:
    users = db.all()
    return sum(u.get("referral_count", 0) for u in users) 