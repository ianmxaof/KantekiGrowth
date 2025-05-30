from .base import PaymentPoller
import aiohttp
import os
import logging
from upgrade_user import upgrade_user
from .processed_hashes import ProcessedHashesStore

TRON_WALLET_ADDRESS = os.getenv("TRON_WALLET_ADDRESS")
processed_hashes = ProcessedHashesStore("processed_tron_hashes.json")

class TronPoller(PaymentPoller):
    poll_interval = 30  # seconds

    async def poll(self):
        if not TRON_WALLET_ADDRESS:
            logging.warning("TRON_WALLET_ADDRESS not set")
            return
        url = f"https://apilist.tronscan.org/api/transaction?address={TRON_WALLET_ADDRESS}&limit=20&start=0&sort=-timestamp"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    for tx in data.get("data", []):
                        tx_hash = tx.get("hash")
                        if tx_hash in processed_hashes:
                            continue
                        # USDT-TRC20 contract type and token
                        if tx.get("contractType") == 31 and tx.get("tokenInfo", {}).get("tokenAbbr") == "USDT":
                            amount = float(tx.get("amount", 0)) / 1e6
                            memo = tx.get("remark") or tx.get("data")  # Use memo/tag for user_id
                            # Map amount to tier
                            if amount == 5:
                                tier = "basic"
                            elif amount == 15:
                                tier = "premium"
                            elif amount == 30:
                                tier = "elite"
                            else:
                                tier = "premium"
                            if memo:
                                upgrade_user(memo, tier)
                                logging.info(f"[TRON] Upgraded user {memo} to {tier} (tx {tx_hash})")
                            processed_hashes.add(tx_hash)
        except Exception as e:
            logging.error(f"[TronPoller] Error polling TRON: {e}") 