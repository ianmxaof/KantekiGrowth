import asyncio
from payments.cryptobot_poller import CryptoBotPoller
from payments.tron_poller import TronPoller
from payments.eth_poller import EthPoller

async def main():
    pollers = [CryptoBotPoller(), TronPoller(), EthPoller()]
    await asyncio.gather(*(p.start() for p in pollers))

if __name__ == '__main__':
    asyncio.run(main()) 