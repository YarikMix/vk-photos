import os
import sys
import math
import time
import logging
from pathlib import Path
from PIL import Image, ImageChops

import yaml
import requests
import aiohttp
import aiofiles
import asyncio
import vk_api
from pytils import numeral

from filter import check_for_duplicates
from functions import (
    decline,
    download_photo,
    download_photos,
    write_json
)


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

loop = asyncio.get_event_loop()


class Utils:
    def create_dir(self, dir_path: Path):
        if not dir_path.exists():
            dir_path.mkdir()

    def remove_dir(self, dir_path: Path):
        if dir_path.exists():
            dir_path.rmdir()

    def auth(self):
        try:
            vk_session = vk_api.VkApi(
                login=config["login"],
                password=config["password"]
            )
            vk_session.auth()
        except Exception as e:
            logging.info("Неправильный логин или пароль")
            print(e)
            exit()
        finally:
            logging.info('Вы успешно авторизовались.')
            return vk_session.get_api()

    def auth_by_token(self):
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

    def check_user_id(self, id: str) -> bool:
        try:
            # Проверяем, существует ли пользователь с таким id
            user = vk.users.get(user_ids=int(id))
            if len(user) != 0: return True
            return False
        except:
            return False

    def check_user_ids(self, ids_list) -> bool:
        try:
            for user_id in ids_list.split(","):
                if not self.check_user_id(user_id):
                    return False
            return True
        except:
            return False

    def check_group_id(self, id: str) -> bool:
        try:
            # Проверяем, существует ли группа с таким id
            group = vk.groups.getById(group_id=int(id))
            if len(group) != 0: return True
            return False
        except:
            return False

    def check_group_ids(self, ids_list) -> bool:
        try:
            for group_id in ids_list.split(","):
                if not self.check_group_id(group_id):
                    return False
            return True
        except:
            return False

    def check_chat_id(self, id: str) -> bool:
        try:
            # Проверяем, существует ли беседа с таким id
            conversation = vk.messages.getConversationsById(peer_ids=2000000000 + int(id))
            if conversation["count"] != 0: return True
            return False
        except:
            return False

    def get_user_id(self):
        return vk.account.getProfileInfo()["id"]

    def get_username(self, user_id: str):
        user = vk.users.get(user_id=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"

    def get_group_title(self, group_id: str):
        group_info = vk.groups.getById(group_id=group_id)
        group_name = group_info[0]["name"].replace("/", " ").replace("|", " ").strip()
        return group_name

    def get_chat_title(self, chat_id: str) -> str:
        chat_title = vk.messages.getConversationsById(
            peer_ids=2000000000 + chat_id
        )["items"][0]["chat_settings"]["title"]
        return chat_title


class UserPhotoDownloader:
    def __init__(self, user_id, parent_dir=DOWNLOADS_DIR):
        self.user_id = int(user_id)
        self.parent_dir = parent_dir

    def get_photos(self):
        # Собираем фото со стены
        photos_by_wall = vk.photos.get(
            user_id=self.user_id,
            album_id="wall",
            photo_sizes=True,
            extended=True
        )["items"]

        # Собираем фото с профиля
        photos_by_profile = vk.photos.get(
            user_id=self.user_id,
            album_id="profile",
            photo_sizes=True,
            extended=True
        )["items"]

        raw_data = photos_by_wall + photos_by_profile
        photos = []

        for photo in raw_data:
            photos.append({
                "id": photo["id"],
                "owner_id": photo["owner_id"],
                "url": photo["sizes"][-1]["url"],
                "likes": photo["likes"]["count"],
                "date": photo["date"]
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

        username = utils.get_username(self.user_id)

        photos_path = self.parent_dir.joinpath(username)
        utils.create_dir(photos_path)

        # Страница пользователя удалена
        if "deactivated" in user_info:
            logging.info("Эта страница удалена")
            utils.remove_dir(photos_path)
        else:
            # Профиль закрыт
            if user_info["is_closed"] and not user_info["can_access_closed"]:
                logging.info(f"Профиль {decline_username} закрыт :(")
                photos = [{
                    "id": self.user_id,
                    "owner_id": self.user_id,
                    "url": user_info["photo_max_orig"],
                    "likes": 0
                }]
            else:
                logging.info(f"Получаем фотографии {decline_username}...")

                # Получаем фотографии пользователя
                photos = self.get_photos()

            # Сортируем фотографии пользователя по дате
            photos.sort(key=lambda k: k["date"], reverse=True)

            logging.info("{} {} {}".format(
                numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
            ))

            time_start = time.time()

            # Скачиваем фотографии пользователя
            await download_photos(photos_path, photos)

            time_finish = time.time()
            download_time = math.ceil(time_finish - time_start)
            logging.info("{} {} за {}".format(
                numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
                numeral.get_plural(download_time, "секунду, секунды, секунд")
            ))


class UsersPhotoDownloader:
    def __init__(self, user_ids: list, parent_dir=DOWNLOADS_DIR):
        self.user_ids = [id for id in user_ids]
        self.parent_dir = parent_dir

    async def main(self):
        for user_id in self.user_ids:
            await UserPhotoDownloader(user_id, self.parent_dir).main()


class GroupPhotoDownloader:
    def __init__(self, group_id: str):
        self.group_id = int(group_id)

    def get_photos(self):
        offset = 0
        while True:
            posts = vk.wall.get(
                owner_id=-self.group_id,
                count=100,
                offset=offset
            )["items"]

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

            if len(posts) < 100:
                break

            offset += 100

    # Todo: понять как использовать get_all_iter
    # def test(self):
    #     self.photos = []
    #     posts = vk.get_all_iter(
    #         method="wall.get",
    #         max_count=500,
    #         values={
    #             "owner_id": -self.group_id,
    #             "count": 100,
    #         }
    #     )
    #     print(len(posts))

    def get_single_post(self, post: dict):
        """
        Проходимся по всем вложениям поста и отбираем только картинки
        """
        for i, attachment in enumerate(post["attachments"]):
            if attachment["type"] == "photo":
                photo_id = post["attachments"][i]["photo"]["id"]
                owner_id = post["attachments"][i]["photo"]["owner_id"]
                photo_url = post["attachments"][i]["photo"]["sizes"][-1]["url"]
                if "likes" in post:
                    likes_count = post["likes"]["count"]
                    self.photos.append({
                        "id": photo_id,
                        "owner_id": -owner_id,
                        "url": photo_url,
                        "likes": likes_count
                    })

    async def main(self):
        # Получаем информацию о группе
        group_info = vk.groups.getById(group_id=self.group_id)[0]
        group_name = group_info["name"].replace("/", " ").replace("|", " ").strip()

        group_dir = DOWNLOADS_DIR.joinpath(group_name)
        utils.create_dir(group_dir)

        self.photos = []

        # Группа закрыта
        if group_info["is_closed"]:
            logging.info(f"Группа '{group_name}' закрыта :(")
            self.photos = [{
                "id": self.group_id,
                "owner_id": self.group_id,
                "url": "https://vk.com/images/community_200.png"
            }]
        else:
            logging.info(f"Получаем фотографии группы '{group_name}'...")

            # Получаем фотографии со стены группы
            self.get_photos()

        # Сортируем фотографии по количеству лайков
        self.photos.sort(key=lambda k: k["likes"], reverse=True)

        logging.info("{} {} {}".format(
            numeral.choose_plural(len(self.photos), "Будет, Будут, Будут"),
            numeral.choose_plural(len(self.photos), "скачена, скачены, скачены"),
            numeral.get_plural(len(self.photos), "фотография, фотографии, фотографий")
        ))

        time_start = time.time()

        # Скачиваем фотографии со стены группы
        await download_photos(group_dir, self.photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logging.info("{} {} за {}".format(
            numeral.choose_plural(len(self.photos), "Скачена, Скачены, Скачены"),
            numeral.get_plural(len(self.photos), "фотография, фотографии, фотографий"),
            numeral.get_plural(download_time, "секунду, секунды, секунд")
        ))

        logging.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(group_dir)
        logging.info(f"Дубликатов удалено: {dublicates_count}")

        logging.info(f"Итого скачено: {len(self.photos) - dublicates_count} фото")


class GroupsPhotoDownloader:
    def __init__(self, group_ids: str):
        self.group_ids = [int(id.strip()) for id in group_ids.split(",")]

    def get_photos(self, group_id: int):
        offset = 0
        while True:
            posts = vk.wall.get(
                owner_id=-group_id,
                count=100,
                offset=offset
            )["items"]

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

            if len(posts) < 100:
                break

            offset += 100

    def get_single_post(self, post: dict):
        """
        Проходимся по всем вложениям поста и отбираем только картинки
        """
        for i, attachment in enumerate(post["attachments"]):
            if attachment["type"] == "photo":
                photo_id = post["attachments"][i]["photo"]["id"]
                owner_id = post["attachments"][i]["photo"]["owner_id"]
                photo_url = post["attachments"][i]["photo"]["sizes"][-1]["url"]
                if "likes" in post:
                    likes_count = post["likes"]["count"]
                    self.photos.append({
                        "id": photo_id,
                        "owner_id": -owner_id,
                        "url": photo_url,
                        "likes": likes_count
                    })

    async def main(self):
        groups_name = ", ".join([utils.get_group_title(group_id) for group_id in self.group_ids])
        photos_path = DOWNLOADS_DIR.joinpath(groups_name)
        utils.create_dir(photos_path)

        self.photos = []

        for group_id in self.group_ids:
            logging.info(f"Получаем фотографии группы '{utils.get_group_title(group_id)}'...")
            self.get_photos(group_id)

        # Сортируем фотографии по количеству лайков
        self.photos.sort(key=lambda k: k["likes"], reverse=True)

        logging.info("{} {} {}".format(
            numeral.choose_plural(len(self.photos), "Будет, Будут, Будут"),
            numeral.choose_plural(len(self.photos), "скачена, скачены, скачены"),
            numeral.get_plural(len(self.photos), "фотография, фотографии, фотографий")
        ))

        time_start = time.time()

        # Скачиваем фотографии со стены группы
        await download_photos(photos_path, self.photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logging.info("{} {} за {}".format(
            numeral.choose_plural(len(self.photos), "Скачена, Скачены, Скачены"),
            numeral.get_plural(len(self.photos), "фотография, фотографии, фотографий"),
            numeral.get_plural(download_time, "секунду, секунды, секунд")
        ))

        logging.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(photos_path)
        logging.info(f"Дубликатов удалено: {dublicates_count}")

        logging.info(f"Итого скачено: {len(self.photos) - dublicates_count} фото")


class ChatMembersPhotoDownloader:
    def __init__(self, chat_id: str):
        self.chat_id = int(chat_id)

    async def main(self):
        chat_title = utils.get_chat_title(self.chat_id)
        chat_path = DOWNLOADS_DIR.joinpath(chat_title)

        # Создаём папку с фотографиями участников беседы, если её не существует
        utils.create_dir(chat_path)

        members = vk.messages.getChat(
            chat_id=self.chat_id
        )["users"]

        if members == []:
            logging.info("Вы вышли из этой беседы")
            utils.remove_dir(chat_path)
        else:
            members_ids = []

            for member_id in members:
                if member_id > 0:
                    members_ids.append(member_id)

            members_ids.remove(utils.get_user_id())

            await UsersPhotoDownloader(user_ids=members_ids, parent_dir=chat_path).main()


class ChatPhotoDownloader:
    def __init__(self, chat_id: str):
        self.chat_id = int(chat_id)

    def download_chat_photo(self):
        """
        Скачиваем аватарку беседы если она есть
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

    def get_attachments(self):
        raw_data = vk.messages.getHistoryAttachments(
            peer_id=2000000000 + self.chat_id,
            media_type="photo"
        )["items"]

        photos = []

        for photo in raw_data:
            photos.append({
                "id": photo["attachment"]["photo"]["id"],
                "owner_id": photo["attachment"]["photo"]["owner_id"],
                "url": photo["attachment"]["photo"]["sizes"][-1]["url"]
            })

        return photos

    async def main(self):
        chat_title = utils.get_chat_title(self.chat_id)
        photos_path = DOWNLOADS_DIR.joinpath(chat_title)
        if not photos_path.exists():
            logging.info(f"Создаём папку с фотографиями беседы '{chat_title}'")
            photos_path.mkdir()

        photos = self.get_attachments()

        logging.info("{} {} {}".format(
            numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
            numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
            numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
        ))

        time_start = time.time()

        # Скачиваем вложения беседы
        await download_photos(photos_path, photos)

        time_finish = time.time()
        download_time = math.ceil(time_finish - time_start)

        logging.info("{} {} за {}".format(
            numeral.choose_plural(len(photos), "Скачена, Скачены, Скачены"),
            numeral.get_plural(len(photos), "фотография, фотографии, фотографий"),
            numeral.get_plural(download_time, "секунду, секунды, секунд")
        ))

        logging.info("Проверка на дубликаты")
        dublicates_count = check_for_duplicates(photos_path)
        logging.info(f"Дубликатов удалено: {dublicates_count}")

        logging.info(f"Итого скачено: {len(photos) - dublicates_count} фото")


if __name__ == '__main__':
    utils = Utils()
    utils.create_dir(DOWNLOADS_DIR)

    print("1. Скачать все фотографии пользователя")
    print("2. Скачать все фотографии нескольких пользователей")
    print("3. Скачать все фотографии со стены группы")
    print("4. Скачать все фотографии нескольких групп")
    print("5. Скачать все фотографии участников беседы")
    print("6. Скачать все вложения беседы")

    while True:
        time.sleep(0.1)
        downloader_type = input("> ")
        if downloader_type == "1":
            vk = utils.auth()
            time.sleep(0.1)
            while True:
                id = input("Введите id пользователя\n> ")
                if utils.check_user_id(id):
                    downloader = UserPhotoDownloader(user_id=id)
                    loop.run_until_complete(downloader.main())
                    break
                else:
                    logging.info("Пользователя с таким id не существует")
                    time.sleep(0.1)
            break
        elif downloader_type == "2":
            vk = utils.auth()
            time.sleep(0.1)
            while True:
                user_ids = input("Введите id пользователей через запятую\n> ")
                if utils.check_user_ids(user_ids):
                    downloader = UsersPhotoDownloader(user_ids=user_ids.split(","))
                    loop.run_until_complete(downloader.main())
                    break
                else:
                    logging.info("Пользователей с таким id не существует")
                    time.sleep(0.1)
            break
        elif downloader_type == "3":
            vk = utils.auth()
            time.sleep(0.1)
            while True:
                id = input("Введите id группы \n> ")
                if utils.check_group_id(id):
                    downloader = GroupPhotoDownloader(group_id=id)
                    loop.run_until_complete(downloader.main())
                    break
                else:
                    logging.info("Группы с таким id не существует")
                    time.sleep(0.1)
            break
        elif downloader_type == "4":
            vk = utils.auth()
            time.sleep(0.1)
            while True:
                group_ids = input("Введите id групп через запятую\n> ")
                if utils.check_group_ids(groups_ids):
                    downloader = GroupsPhotoDownloader(group_ids=group_ids)
                    loop.run_until_complete(downloader.main())
                    break
                else:
                    logging.info("Групп с таким id не существует")
                    time.sleep(0.1)
            break
        elif downloader_type == "5":
            vk = utils.auth_by_token()
            time.sleep(0.1)
            while True:
                id = input("Введите id беседы\n> ")
                if utils.check_chat_id(id):
                    downloader = ChatMembersPhotoDownloader(chat_id=id)
                    loop.run_until_complete(downloader.main())
                    break
                else:
                    logging.info("Беседы с таким id не существует")
                    time.sleep(0.1)
            break
        elif downloader_type == "6":
            vk = utils.auth_by_token()
            time.sleep(0.1)
            while True:
                id = input("Введите id беседы\n> ")
                if utils.check_chat_id(id):
                    downloader = ChatPhotoDownloader(chat_id=id)
                    loop.run_until_complete(downloader.main())
                    break
                else:
                    logging.info("Беседы с таким id не существует")
                    time.sleep(0.1)
            break
        else:
            logging.info("Неправильная команда")

    if VK_CONFIG_PATH.exists():
        VK_CONFIG_PATH.unlink()