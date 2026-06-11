import asyncio
from services.forte_rates import fetch_rates

async def main():
    rates = await fetch_rates()
    print("Fetched rates:", rates)

if __name__ == "__main__":
    asyncio.run(main())
