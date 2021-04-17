import math
import time
import logging
from pathlib import Path

import yaml
import aiohttp
import aiofiles
import asyncio
import vk_api
from vk_api import audio
from tqdm.asyncio import tqdm
from pytils import numeral

from functions import decline


BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR.joinpath("Фотки")
CONFIG_PATH = BASE_DIR.joinpath("config.yaml")
VK_CONFIG_PATH = BASE_DIR.joinpath("vk_config.v2.json")

with open(CONFIG_PATH, encoding="utf-8") as ymlFile:
    config = yaml.load(ymlFile.read(), Loader=yaml.Loader)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=logging.INFO
)

logger = logging.getLogger('vk_api')
logger.disabled = True

def auth_handler(remember_device=None):
    code = input("Введите код подтверждения\n> ")
    if remember_device is None:
        remember_device = True
    return code, remember_device

def auth():
    vk_session = vk_api.VkApi(
        login=config["login"],
        password=config["password"],
        auth_handler=auth_handler
    )
    try:
        vk_session.auth()
    except Exception as e:
        logging.info("Неправильный логин или пароль")
        exit()
    finally:
        logging.info('Вы успешно авторизовались.')
        return vk_session

def check_id(id: str):
    """Проверяем id на валидность"""
    try:
        id = int(id)
        if id > 0:
            # Проверяем, существует ли пользователь с таким id
            user = vk.users.get(user_ids=id)
            if len(user) != 0:
                return "user"
        else:
            # Проверяем, существует ли группа с таким id
            group = vk.groups.getById(group_id=abs(id))
            if len(group) != 0:
                return "group"
    except:
        return None


class UsersPhotoDownloader:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_photos(self):
        # Собираем фото со стены
        photos_by_wall = vk.photos.get(
            user_id=self.user_id,
            album_id="wall",
            photo_sizes=True
        )["items"]

        # Собираем фото с профиля
        photos_by_profile = vk.photos.get(
            user_id=self.user_id,
            album_id="profile",
            photo_sizes=True
        )["items"]

        raw_data = photos_by_wall + photos_by_profile
        photos = []

        for photo in raw_data:
            photos.append({
                "id": photo["id"],
                "owner_id": photo["owner_id"],
                "url": photo["sizes"][-1]["url"]
            })

        return photos

    async def download_photo(self, session, photo_url, photo_path):
        """Скачивает фото"""
        async with session.get(photo_url) as response:
            if response.status == 200:
                async with aiofiles.open(photo_path, "wb") as f:
                    await f.write(await response.read())
                    await f.close()

    async def download_photos(self, photos: list):
        """Скачивает все фото из переданного списка"""
        async with aiohttp.ClientSession() as session:
            futures = []
            for photo in photos:
                photo_title = "{}_{}.jpg".format(photo["id"], photo["owner_id"])
                photo_path = self.user_photos_path.joinpath(photo_title)
                futures.append(self.download_photo(session, photo["url"], photo_path))

            for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
                await future

    async def main(self):
        user_info = vk.users.get(
            user_ids=self.user_id,
            fields="sex, photo_max_orig"
        )[0]

        decline_username = decline(
            first_name=user_info["first_name"],
            last_name=user_info["last_name"],
            sex=user_info["sex"]
        )

        # Страница пользователя удалена
        if "deactivated" in user_info:
            logging.info("Эта страница удалена")
        else:
            username = f"{user_info['first_name']} {user_info['last_name']}"

            self.user_photos_path = PHOTOS_DIR.joinpath(username)

            # Создаём папку c фотографиями пользователя, если её не существует
            if not self.user_photos_path.exists():
                logging.info(f"Создаём папку с фотографиями {decline_username}")
                self.user_photos_path.mkdir()

            photos = []

            # Профиль закрыт
            if user_info["is_closed"] and not user_info["can_access_closed"]:
                logging.info(f"Профиль {decline_username} закрыт :(")
                photo_url = user_info["photo_max_orig"]
                if photo_url == "https://vk.com/images/camera_400.png":
                    logging.info("У пользователя нет аватарки")
                else:
                    photos = [{
                        "id": self.user_id,
                        "owner_id": self.user_id,
                        "url": photo_url
                    }]
            else:
                logging.info("Получаем фотографии...")

                # Получаем фотографии пользователя
                photos = self.get_photos()

            logging.info("{} {} {}".format(
                numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
            ))

            time_start = time.time()

            # Скачиваем фотографии пользователя
            await self.download_photos(photos)

            time_finish = time.time()
            download_time = math.ceil(time_finish - time_start)
            logging.info("{} {} за {}".format(
                numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
                numeral.get_plural(download_time, "секунду, секунды, секунд")
            ))


class GroupsPhotoDownloader:
    def __init__(self, group_id):
        self.group_id=group_id

    def get_photos(self):
        self.photos = []

        offset = 0
        while True:
            posts = vk.wall.get(
                owner_id=self.group_id,
                count=100,
                offset=offset
            )["items"]

            self.filter_posts(posts)

            if len(posts) < 100:
                break

            offset += 100

        return self.photos

    def filter_posts(self, posts: list):
        for post in posts:

            # Пропускаем посты с рекламой
            if post["marked_as_ads"]:
                continue

            # Если пост скопирован с другой группы
            if "copy_history" in post:
                if "attachments" in post["copy_history"][0]:
                    self.get_single_post(post["copy_history"][0])

            elif "attachments" in post:
                self.get_single_post(post)

    def get_single_post(self, post: dict):
        # Проходимся по всем вложениям поста
        for i, attachment in enumerate(post["attachments"]):
            # Отбираем только картинки
            if attachment["type"] == "photo":
                photo_id = post["attachments"][i]["photo"]["id"]
                owner_id = post["attachments"][i]["photo"]["owner_id"]
                photo_url = post["attachments"][i]["photo"]["sizes"][-1]["url"]
                self.photos.append({
                    "id": photo_id,
                    "owner_id": -owner_id,
                    "url": photo_url
                })

    async def download_photo(self, session: aiohttp.ClientSession, photo_url: str, photo_path: Path):
        """Скачивает фото"""
        async with session.get(photo_url) as response:
            if response.status == 200:
                async with aiofiles.open(photo_path, "wb") as f:
                    await f.write(await response.read())
                    await f.close()

    async def download_photos(self, photos: list):
        """Скачивает все фото из переданного списка"""
        async with aiohttp.ClientSession() as session:
            futures = []
            for photo in photos:
                photo_title = "{}_{}.jpg".format(photo["id"], photo["owner_id"])
                photo_path = self.group_photos_path.joinpath(photo_title)
                futures.append(self.download_photo(session, photo["url"], photo_path))

            for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
                await future

    async def main(self):
        # Получаем информацию о группе
        group_info = vk.groups.getById(group_id=abs(self.group_id))[0]
        group_name = group_info["name"].replace("/", " ").replace("|", " ").strip()

        self.group_photos_path = PHOTOS_DIR.joinpath(group_name)

        # Создаём папку c фотографиями группы, если её не существует
        if not self.group_photos_path.exists():
            logging.info(f"Создаём папку с фотографиями группы '{group_name}'")
            self.group_photos_path.mkdir()

        # Группа закрыта
        if group_info["is_closed"]:
            logging.info(f"Группа '{group_name}' закрыта :(")

            max_size = list(group_info)[-1]
            photo_url = group_info[max_size]
            photos = [{
                "id": -self.group_id,
                "owner_id": -self.group_id,
                "url": photo_url
            }]
        else:
            logging.info(f"Получаем фотографии...")

            # Получаем фотографии со стены группы
            photos = self.get_photos()

        logging.info("{} {} {}".format(
            numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
            numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
            numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
        ))

        time_start = time.time()

        # Скачиваем фотографии со стены группы
        await self.download_photos(photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)
        logging.info("{} {} за {}".format(
            numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
            numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
            numeral.get_plural(download_time, "секунду, секунды, секунд")
        ))


if __name__ == '__main__':
    # Создаём папку c загрузками, если её не существует
    if not PHOTOS_DIR.exists():
        PHOTOS_DIR.mkdir()

    vk_session = auth()
    vk = vk_session.get_api()
    vk_audio = audio.VkAudio(vk_session)

    loop = asyncio.get_event_loop()

    id = input("Введите id человека, либо id группы(со знаком минус)\n> ")
    id_type = check_id(id)
    if id_type == "user":
        downloader = UsersPhotoDownloader(user_id=int(id))
        loop.run_until_complete(downloader.main())
    elif id_type == "group":
        downloader = GroupsPhotoDownloader(group_id=int(id))
        loop.run_until_complete(downloader.main())
    else:
        logging.info("Пользователя / группы с таким id не существует")

    VK_CONFIG_PATH.unlink()  # Удаляем конфиг вк