import aiohttp


http_session: aiohttp.ClientSession | None = None


async def init_http_session():
    global http_session
    if http_session is None:
        http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"Origin": "https://mgm.gov.tr"}
        )


async def close_http_session():
    global http_session
    if http_session is not None:
        await http_session.close()
        http_session = None


async def fetch_sst_data():
    if http_session is None:
        raise RuntimeError("HTTP session is not initialized")
    async with http_session.get(
        "https://servis.mgm.gov.tr/web/sondurumlar/denizler",
        ssl=False,
    ) as response:
        response.raise_for_status()
        return await response.json()
