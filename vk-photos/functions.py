import json
from pathlib import Path

import aiohttp
import aiofiles
import asyncio
from tqdm.asyncio import tqdm
from pytrovich.enums import NamePart, Gender, Case
from pytrovich.maker import PetrovichDeclinationMaker


maker = PetrovichDeclinationMaker()

def decline(first_name, last_name, sex):
    """Возвращает имя и фамилию в родительном падаже."""
    if sex == 1:
        first_name = maker.make(NamePart.FIRSTNAME, Gender.FEMALE, Case.GENITIVE, first_name)
        last_name = maker.make(NamePart.LASTNAME, Gender.FEMALE, Case.GENITIVE, last_name)
    elif sex == 2:
        first_name = maker.make(NamePart.FIRSTNAME, Gender.MALE, Case.GENITIVE, first_name)
        last_name = maker.make(NamePart.LASTNAME, Gender.MALE, Case.GENITIVE, last_name)
    return f"{first_name} {last_name}"

def write_json(data, title="data"):
    with open(title + ".json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

async def download_photo(session: aiohttp.ClientSession, photo_url: str, photo_path: Path):
    try:
        if not photo_path.exists():
            async with session.get(photo_url) as response:
                if response.status == 200:
                    async with aiofiles.open(photo_path, "wb") as f:
                        await f.write(await response.read())
    except Exception as e:
        print(e)

async def download_photos(photos_path: Path, photos: list):
    async with aiohttp.ClientSession() as session:
        futures = []
        for i, photo in enumerate(photos, start=1):
            photo_title = "{}_{}_{}_{}.jpg".format(i, photo["likes"], photo["owner_id"], photo["id"])
            photo_path = photos_path.joinpath(photo_title)
            futures.append(download_photo(session, photo["url"], photo_path))

        for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
            await future