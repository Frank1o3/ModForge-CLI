import asyncio

from modforge_cli.api import ModrinthAPIConfig
from modforge_cli.core import get_api_session

api = ModrinthAPIConfig()

url = api.search("Fabric API", game_versions=["1.21.11"], loaders=["fabric"])

async def run() -> None:
    async with await get_api_session() as session, await session.get(url) as res:
        if res.status != 200:
            print("Error on request")
            return
        data = await res.json()
        print(data["hits"][0]["server_side"], data["hits"][0]["client_side"])

asyncio.run(run())