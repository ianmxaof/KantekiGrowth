from .base import PaymentPoller
import aiohttp
import os
import logging
from upgrade_user import upgrade_user
from .processed_hashes import ProcessedHashesStore

ETH_WALLET_ADDRESS = os.getenv("ETH_WALLET_ADDRESS")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
USDT_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # Mainnet USDT
processed_hashes = ProcessedHashesStore("processed_eth_hashes.json")

class EthPoller(PaymentPoller):
    poll_interval = 30  # seconds

    async def poll(self):
        if not ETH_WALLET_ADDRESS or not ETHERSCAN_API_KEY:
            logging.warning("ETH_WALLET_ADDRESS or ETHERSCAN_API_KEY not set")
            return
        url = (
            f"https://api.etherscan.io/api"
            f"?module=account&action=tokentx"
            f"&contractaddress={USDT_CONTRACT}"
            f"&address={ETH_WALLET_ADDRESS}"
            f"&page=1&offset=20&sort=desc"
            f"&apikey={ETHERSCAN_API_KEY}"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    for tx in data.get("result", []):
                        tx_hash = tx.get("hash")
                        if tx_hash in processed_hashes:
                            continue
                        amount = float(tx.get("value", 0)) / 1e6
                        memo = tx.get("input")  # You may need to parse input data for memo/user_id
                        # Map amount to tier
                        if amount == 5:
                            tier = "basic"
                        elif amount == 15:
                            tier = "premium"
                        elif amount == 30:
                            tier = "elite"
                        else:
                            tier = "premium"
                        # You may need to map memo to user_id, or use a different field
                        if memo:
                            upgrade_user(memo, tier)
                            logging.info(f"[ETH] Upgraded user {memo} to {tier} (tx {tx_hash})")
                        processed_hashes.add(tx_hash)
        except Exception as e:
            logging.error(f"[EthPoller] Error polling ETH: {e}") 