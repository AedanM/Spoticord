import asyncio
from datetime import datetime

import polars as pd
from Defines import USER_DATA_FILE, RequestResults

CURRENT_USER_DATA: pd.DataFrame = pd.read_csv(USER_DATA_FILE)
FILE_LOCK = asyncio.Lock()


async def LogUserData(
    trackInfo: tuple[str, str, str], user: str, status: RequestResults, isTesting
) -> None:
    message = f"\n{datetime.now()},{user},{status},{','.join(trackInfo)}"
    if isTesting:
        print(message)
    else:
        async with FILE_LOCK:
            with USER_DATA_FILE.open(mode="a", encoding="utf-8") as fp:
                fp.write(message)
                # todo: make this more robust and less slow
                CURRENT_USER_DATA = pd.read_csv(USER_DATA_FILE)
