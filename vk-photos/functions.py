import json
from pathlib import Path

import aiohttp
import aiofiles
import asyncio
from tqdm.asyncio import tqdm
from pytrovich.enums import NamePart, Gender, Case
from pytrovich.maker import PetrovichDeclinationMaker
import yt_dlp

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
            photo_title = "{}_{}.jpg".format(photo["owner_id"], photo["id"])
            photo_path = photos_path.joinpath(photo_title)
            futures.append(download_photo(session, photo["url"], photo_path))

        for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
            await future

async def download_video(video_path, video_link):
    ydl_opts = {'outtmpl': '{}'.format(video_path), 'quiet': True, 'retries': 10}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(video_link)
        print("Видео загружено: {}".format(video_link))

async def download_videos(videos_path: Path, videos: list):
    futures = []
    for i, video in enumerate(videos, start=1):
        filename = "{}_{}.mp4".format(video["owner_id"], video["id"])#, video["title"])
        video_path = videos_path.joinpath(filename)
        futures.append(download_video(video_path, video["player"]))
    print(len(futures))
    for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
        await future
            