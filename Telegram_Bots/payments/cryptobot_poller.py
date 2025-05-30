from .base import PaymentPoller
import aiohttp
import os
import logging
from upgrade_user import upgrade_user
from .processed_hashes import ProcessedHashesStore

CRYPTOBOT_API_TOKEN = os.getenv("CRYPTOBOT_API_TOKEN")
processed_payments = ProcessedHashesStore("processed_cryptobot_payments.json")

class CryptoBotPoller(PaymentPoller):
    poll_interval = 30  # seconds

    async def poll(self):
        if not CRYPTOBOT_API_TOKEN:
            logging.warning("CRYPTOBOT_API_TOKEN not set")
            return
        url = f"https://api.cryptobot.com/payments?token={CRYPTOBOT_API_TOKEN}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    for payment in data.get("result", []):
                        payment_id = str(payment.get("id"))
                        if payment_id in processed_payments:
                            continue
                        if payment["status"] == "completed":
                            user_id = payment.get("comment")  # Store user_id in comment
                            amount = float(payment["amount"])
                            currency = payment["asset"]
                            # Map amount/currency to tier
                            if amount == 5 and currency == "USDT":
                                tier = "basic"
                            elif amount == 15 and currency == "USDT":
                                tier = "premium"
                            elif amount == 30 and currency == "USDT":
                                tier = "elite"
                            else:
                                tier = "premium"
                            if user_id:
                                upgrade_user(user_id, tier)
                                logging.info(f"[CryptoBot] Upgraded user {user_id} to {tier} (payment {payment_id})")
                            processed_payments.add(payment_id)
        except Exception as e:
            logging.error(f"[CryptoBotPoller] Error polling payments: {e}") 