import asyncio

class PaymentPoller:
    poll_interval = 30  # seconds

    async def poll(self):
        raise NotImplementedError

    async def start(self):
        while True:
            await self.poll()
            await asyncio.sleep(self.poll_interval) 