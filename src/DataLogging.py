import asyncio
from datetime import date

import polars as pd
from Defines import USER_DATA_FILE, RequestResults

CURRENT_USER_DATA: pd.DataFrame = pd.DataFrame()
FILE_LOCK = asyncio.Lock()


async def LogUserData(trackInfo: tuple[str, str, str], user: str, status: RequestResults) -> None:
    message = f"\n{date.today()},{user},{status},{','.join(trackInfo)}"

    async with FILE_LOCK:
        with USER_DATA_FILE.open(mode="a", encoding="utf-8") as fp:
            fp.write(message)
            # todo: make this more robust and less slow
            CURRENT_USER_DATA = pd.read_csv(USER_DATA_FILE)
