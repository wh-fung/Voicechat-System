"""
Start the voicechat system server
"""

import asyncio
from system import SystemServer


async def main():
    system = SystemServer()
    await system.start()
    await asyncio.Future()


if __name__ == "__main__":
    print("Starting system server")
    asyncio.run(main())
    
