import math
import time
import logging
from pathlib import Path

import yaml
import requests
import aiohttp
import aiofiles
import asyncio
import vk_api
from tqdm.asyncio import tqdm
from pytils import numeral

from functions import decline


BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR.joinpath("Фотки")
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

# Создаём папку c загрузками, если её не существует
if not DOWNLOADS_DIR.exists():
    DOWNLOADS_DIR.mkdir()

loop = asyncio.get_event_loop()

def auth_handler(remember_device=None):
    code = input("Введите код подтверждения\n> ")
    if remember_device is None:
        remember_device = True
    return code, remember_device

def auth():
    try:
        vk_session = vk_api.VkApi(
            login=config["login"],
            password=config["password"]
        )
        vk_session.auth()
    except Exception as e:
        logging.info("Неправильный логин или пароль")
        exit()
    finally:
        logging.info('Вы успешно авторизовались.')
        return vk_session.get_api()

def auth_by_token():
    try:
        vk_session = vk_api.VkApi(
            token=config["token"]
        )
    except Exception as e:
        logging.info("Неправильный токен")
        logging.info("Токен можно получить здесь https://vkhost.github.io/")
        exit()
    finally:
        logging.info('Вы успешно авторизовались.')
        return vk_session.get_api()

def check_user_id(id: str):
    try:
        # Проверяем, существует ли пользователь с таким id
        user = vk.users.get(user_ids=int(id))
        if len(user) != 0: return True
        return False
    except:
        return False

def check_group_id(id: str):
    try:
        # Проверяем, существует ли группа с таким id
        group = vk.groups.getById(group_id=int(id))
        if len(group) != 0: return True
        return False
    except:
        return False

def check_chat_id(id: str):
    try:
        # Проверяем, существует ли беседа с таким id
        conversation = vk.messages.getConversationsById(peer_ids=2000000000 + int(id))
        if conversation["count"] != 0: return True
        return False
    except:
        return False

def get_user_id():
    return vk.account.getProfileInfo()["id"]

def get_username(user_id: str):
    user = vk.users.get(user_id=user_id)[0]
    return f"{user['first_name']} {user['last_name']}"

async def download_photo(session: aiohttp.ClientSession, photo_url: str, photo_path: Path):
    async with session.get(photo_url) as response:
        if response.status == 200:
            async with aiofiles.open(photo_path, "wb") as f:
                await f.write(await response.read())

async def download_photos(photos_path: Path, photos: list):
    async with aiohttp.ClientSession() as session:
        futures = []
        for photo in photos:
            photo_title = "{}_{}.jpg".format(photo["owner_id"], photo["id"])
            photo_path = photos_path.joinpath(photo_title)
            futures.append(download_photo(session, photo["url"], photo_path))

        for future in tqdm(asyncio.as_completed(futures), total=len(futures)):
            await future


class UserPhotoDownloader:
    def __init__(self, photos_dir: Path, user_id: str):
        self.photos_dir = photos_dir
        self.user_id = int(user_id)

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
            self.photos_path = self.photos_dir.joinpath(username)

            # Создаём папку c фотографиями пользователя, если её не существует
            if not self.photos_path.exists():
                logging.info(f"Создаём папку с фотографиями {decline_username}")
                self.photos_path.mkdir()

            photos = []

            # Профиль закрыт
            if user_info["is_closed"] and not user_info["can_access_closed"]:
                logging.info(f"Профиль {decline_username} закрыт :(")
                photo_url = user_info["photo_max_orig"]
                if photo_url == "https://vk.com/images/camera_400.png":
                    logging.info(f"У {decline_username} нет аватарки")
                else:
                    photos = [{
                        "id": self.user_id,
                        "owner_id": self.user_id,
                        "url": photo_url
                    }]
            else:
                logging.info(f"Получаем фотографии {decline_username}...")

                # Получаем фотографии пользователя
                photos = self.get_photos()

            logging.info("{} {} {}".format(
                numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
            ))

            time_start = time.time()

            # Скачиваем фотографии пользователя
            await download_photos(self.photos_path, photos)

            time_finish = time.time()
            download_time = math.ceil(time_finish - time_start)
            logging.info("{} {} за {}".format(
                numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
                numeral.get_plural(download_time, "секунду, секунды, секунд")
            ))


class GroupPhotoDownloader:
    def __init__(self, group_id: str):
        self.group_id = int(group_id)

    def get_photos(self) -> list:
        """Возвращает список всех фото со стены группы"""
        self.photos = []

        offset = 0
        while True:
            posts = vk.wall.get(
                owner_id=-self.group_id,
                count=100,
                offset=offset
            )["items"]

            self.filter_posts(posts)

            if len(posts) < 100:
                break

            offset += 100

        return self.photos

    def filter_posts(self, posts: list):
        """
        Фильтруем посты на наличие рекламы
        """
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
        """
        Проходимся по всем вложениям поста и отбираем только картинки
        """
        for i, attachment in enumerate(post["attachments"]):
            if attachment["type"] == "photo":
                photo_id = post["attachments"][i]["photo"]["id"]
                owner_id = post["attachments"][i]["photo"]["owner_id"]
                photo_url = post["attachments"][i]["photo"]["sizes"][-1]["url"]
                self.photos.append({
                    "id": photo_id,
                    "owner_id": -owner_id,
                    "url": photo_url
                })

    async def main(self):
        # Получаем информацию о группе
        group_info = vk.groups.getById(group_id=self.group_id)[0]
        group_name = group_info["name"].replace("/", " ").replace("|", " ").strip()

        group_photos_path = DOWNLOADS_DIR.joinpath(group_name)

        # Создаём папку c фотографиями группы, если её не существует
        if not group_photos_path.exists():
            logging.info(f"Создаём папку с фотографиями группы '{group_name}'")
            group_photos_path.mkdir()

        # Группа закрыта
        if group_info["is_closed"]:
            logging.info(f"Группа '{group_name}' закрыта :(")

            max_size = list(group_info)[-1]
            photo_url = group_info[max_size]
            photos = [{
                "id": self.group_id,
                "owner_id": self.group_id,
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
        await download_photos(group_photos_path, photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logging.info("{} {} за {}".format(
            numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
            numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
            numeral.get_plural(download_time, "секунду, секунды, секунд")
        ))


class ChatPhotoDownloader:
    def __init__(self, chat_id: str):
        self.chat_id = int(chat_id)

    def get_members(self) -> list:
        """
        Возвращает список из id участников беседы (не считая ботов и самого себя)
        """
        members = vk.messages.getChat(
            chat_id=self.chat_id
        )["users"]

        members_ids = []

        for member_id in members:
            if member_id > 0:
                members_ids.append(member_id)

        members_ids.remove(get_user_id())

        return members_ids

    def download_chat_photo(self):
        """
        Скачивает аватарку беседы если она есть
        """
        if "photo" in self.chat:
            sizes = self.chat["photo"]
            max_size = list(sizes)[-2]
            photo_url = sizes[max_size]
            photo_path = self.chat_dir.joinpath("Аватарка беседы.png")

            response = requests.get(photo_url)
            if response.status_code == 200:
                with open(photo_path, mode="wb") as f:
                    f.write(response.content)

    async def main(self):
        self.chat = vk.messages.getConversationsById(
            peer_ids=2000000000 + self.chat_id
        )["items"][0]["chat_settings"]
        chat_name = self.chat["title"]

        # Создаём папку с фотографиями участников беседы, если её не существует
        self.chat_dir = DOWNLOADS_DIR.joinpath(chat_name)
        if not self.chat_dir.exists():
            logging.info(f"Создаём папку с фотографиями участников беседы '{chat_name}'")
            self.chat_dir.mkdir()

        logging.info("Скачиваем аватарку беседы")
        self.download_chat_photo()
        members = self.get_members()

        for user_id in members:
            user_photo_downloader = UserPhotoDownloader(photos_dir=self.chat_dir, user_id=user_id)
            await user_photo_downloader.main()


if __name__ == '__main__':
    print("1. Скачать все фотографии пользователя")
    print("2. Скачать все фотографии со стены группы")
    print("3. Скачать все фотографии пользователей беседы")
    downloader_type = input("> ")

    if downloader_type == "1":
        vk = auth()
        time.sleep(1)
        id = input("Введите id человека\n> ")
        if check_user_id(id):
            username = get_username(user_id=id)
            downloader = UserPhotoDownloader(photos_dir=DOWNLOADS_DIR, user_id=id)
            loop.run_until_complete(downloader.main())
        else:
            print("Пользователя с таким id не существует")
    elif downloader_type == "2":
        vk = auth()
        time.sleep(1)
        id = input("Введите id группы\n> ")
        if check_group_id(id):
            downloader = GroupPhotoDownloader(group_id=id)
            loop.run_until_complete(downloader.main())
        else:
            print("Группы с таким id не существует")
    elif downloader_type == "3":
        vk = auth_by_token()
        time.sleep(1)
        id = input("Введите id беседы\n> ")
        if check_chat_id(id):
            downloader = ChatPhotoDownloader(chat_id=id)
            loop.run_until_complete(downloader.main())
        else:
            print("Беседы с таким id не существует")
    else:
        logging.info("Введите 1, 2 или 3")

    if VK_CONFIG_PATH.exists():
        VK_CONFIG_PATH.unlink()