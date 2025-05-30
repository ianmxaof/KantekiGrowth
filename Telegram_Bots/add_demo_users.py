from tinydb import TinyDB

db = TinyDB('users.json')

demo_users = [
    {
        "user_id": 1001,
        "username": "alice",
        "tier": "basic",
        "referral_count": 2,
        "badges": ["starter"],
        "last_active": "2024-05-30T12:00:00"
    },
    {
        "user_id": 1002,
        "username": "bob",
        "tier": "premium",
        "referral_count": 5,
        "badges": ["referrer", "premium"],
        "last_active": "2024-05-30T13:00:00"
    },
    {
        "user_id": 1003,
        "username": "carol",
        "tier": "elite",
        "referral_count": 10,
        "badges": ["elite", "top-referrer"],
        "last_active": "2024-05-30T14:00:00"
    }
]

for user in demo_users:
    db.upsert(user, lambda u: u['user_id'] == user['user_id'])

print("Demo users added to users.json") 