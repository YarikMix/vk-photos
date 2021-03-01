# -*- coding: utf-8 -*-
import time
import threading
from pathlib import Path

import requests
import vk_api
import yaml
from tqdm import tqdm
from pytils import numeral

from functions import decline


BASE_DIR = Path(__file__).resolve().parent
PHOTOS_DIR = BASE_DIR.joinpath("Фотки")
CONFIG_PATH = BASE_DIR.joinpath("config.yaml")

with open(CONFIG_PATH) as ymlFile:
    config = yaml.load(ymlFile.read(), Loader=yaml.Loader)

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
        return vk_session.get_api()
    except:
        print("Неправильный логин или пароль")
        return None

def check_id(id):
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
    def __init__(self, user_id):
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
                "url": photo["sizes"][-1]["url"]
            })

        return photos

    def download_photos(self, photos):
        """Скачиваем все фото из переданного списка"""

        # Number of parallel threads
        self.lock = threading.Semaphore(4)

        # List of threads objects I so we can handle them later
        thread_pool = []

        pbar = tqdm(total=len(photos))

        for photo in photos:
            thread = threading.Thread(target=self.download_single_photo, args=(photo,))
            thread_pool.append(thread)
            thread.start()

            # Add one to our lock, so we will wait if needed.
            self.lock.acquire()

            pbar.update(1)

        pbar.close()

        for thread in thread_pool:
            thread.join()

    def download_single_photo(self, photo):
        photo_id = photo["id"]
        photo_url = photo["url"]
        file_name = f"{photo_id}.jpg"
        file_path = self.user_photos_path.joinpath(file_name)

        # Если фото ещё не скачено, то скачиваем его
        if not file_path.exists():
            r = requests.get(photo_url)
            with open(file_path, "wb") as f:
                f.write(r.content)

        self.lock.release()

    def main(self):
        user_info = vk.users.get(
            user_ids=self.user_id,
            fields="sex"
        )[0]

        # Если страница пользователя удалена
        if "deactivated" in user_info:
            print("Эта страница удалена")
        else:
            decline_username = decline(
                first_name=user_info["first_name"],
                last_name=user_info["last_name"],
                sex=user_info["sex"]
            )

            if user_info["is_closed"] and not user_info["can_access_closed"]:
                print(f"Профиль {decline_username} закрыт")
            else:
                username = f"{user_info['first_name']} {user_info['last_name']}"
                self.user_photos_path = PHOTOS_DIR.joinpath(username)

                # Создаём папку c фотографиями пользователя, если её не существует
                if not self.user_photos_path.exists():
                    print(f"Создаём папку с фотографиями {decline_username}")
                    self.user_photos_path.mkdir()

                photos = self.get_photos()
                print("{} {} {}".format(
                    numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                    numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                    numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
                ))

                time_start = time.time()
                self.download_photos(photos)

                time_finish = time.time()
                download_time = round(time_finish - time_start)
                print("{} {} за {}".format(
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

    def filter_posts(self, posts):
        for post in posts:

            # Пропускаем посты с рекламой
            if post["marked_as_ads"]:
                continue

            if "copy_history" in post:
                if "attachments" in post["copy_history"][0]:
                    # Проходимся по всем вложениям поста
                    for i, attachment in enumerate(post["copy_history"][0]["attachments"]):
                        # Отбираем только картинки
                        if attachment["type"] == "photo":
                            photo_id = post["copy_history"][0]["attachments"][i]["photo"]["id"]
                            photo_url = post["copy_history"][0]["attachments"][i]["photo"]["sizes"][-1]["url"]

                            self.photos.append({
                                "id": photo_id,
                                "url": photo_url
                            })
            elif "attachments" in post:
                # Проходимся по всем вложениям поста
                for i, attachment in enumerate(post["attachments"]):
                    # Отбираем только картинки
                    if attachment["type"] == "photo":
                        photo_id = post["attachments"][i]["photo"]["id"]
                        photo_url = post["attachments"][i]["photo"]["sizes"][-1]["url"]

                        self.photos.append({
                            "id": photo_id,
                            "url": photo_url
                        })


    def get_single_photo_data(self, post):
        try:
            if "copy_history" in post:
                photo_id = post["copy_history"][0]["attachments"][0]["photo"]["id"]
                photo_url = post["copy_history"][0]["attachments"][0]["photo"]["sizes"][-1]["url"]
                return {
                    "id": str(photo_id),
                    "url": photo_url
                }
            else:
                photo_id = post["attachments"][0]["photo"]["id"]
                photo_url = post["attachments"][0]["photo"]["sizes"][-1]["url"]
                return {
                    "id": str(photo_id),
                    "url": photo_url
                }
        except:
            return None

    def download_photos(self, photos):
        """Скачиваем все фото из переданного списка"""

        self.lock = threading.Semaphore(4)

        thread_pool = []

        self.total_count = 0  # Количество скаченных фото
        pbar = tqdm(total=len(photos))

        for photo in photos:
            thread = threading.Thread(target=self.download_single_photo, args=(photo,))
            thread_pool.append(thread)
            thread.start()

            self.lock.acquire()

            pbar.update(1)

        pbar.close()

        for thread in thread_pool:
            thread.join()

    def download_single_photo(self, photo):
        photo_id = photo["id"]
        photo_url = photo["url"]
        file_name = f"{photo_id}.jpg"
        file_path = self.group_photos_path.joinpath(file_name)

        # Если фото ещё не скачено, то скачиваем его
        if not file_path.exists():
            r = requests.get(photo_url)
            with open(file_path, "wb") as f:
                f.write(r.content)
                self.total_count += 1

        self.lock.release()

    def get_group_info(self):
        """Получаем название группы, а также информацию о том закрыта ли она"""
        data = vk.groups.getById(
            group_id=abs(self.group_id)
        )

        self.group_name = data[0]["name"].replace("/", " ").replace("|", " ").strip()
        self.is_closed = data[0]["is_closed"]

    def main(self):
        self.get_group_info()  # Получаем информацию о группе

        # Если группа закрыта, то завершаем программу
        if self.is_closed:
            print(f"Группа '{self.group_name}' закрыта")
        else:
            self.group_photos_path = PHOTOS_DIR.joinpath(self.group_name)

            # Создаём папку c фотографиями группы, если её не существует
            if not self.group_photos_path.exists():
                print(f"Создаём папку с фотографиями группы '{self.group_name}'")
                self.group_photos_path.mkdir()

            print("Получаем фотографии группы")
            photos = self.get_photos()  # Получаем фотографии со стены группы
            print("{} {} {}".format(
                numeral.choose_plural(len(photos), "Будет, Будут, Будут"),
                numeral.choose_plural(len(photos), "скачена, скачены, скачены"),
                numeral.get_plural(len(photos), "фотография, фотографии, фотографий")
            ))

            print("Начинаем скачивать фотографии")
            time_start = time.time()
            self.download_photos(photos)  # Скачиваем фотографии

            time_finish = time.time()
            download_time = round(time_finish - time_start)
            print("{} {} за {}".format(
                numeral.choose_plural(self.total_count, "Скачена, Скачены, Скачены"),
                numeral.get_plural(self.total_count, "фотография, фотографии, фотографий"),
                numeral.get_plural(download_time, "секунду, секунды, секунд")
            ))


if __name__ == '__main__':
    # Создаём папку c фотографиями, если её не существует
    if not PHOTOS_DIR.exists():
        PHOTOS_DIR.mkdir()

    vk = auth()

    if vk != None:
        id = input("Введите id человека, либо id группы(со знаком минус)\n> ")
        if check_id(id) == "user":
            Downloader = UsersPhotoDownloader(user_id=int(id))
            Downloader.main()
        elif check_id(id) == "group":
            Downloader = GroupsPhotoDownloader(group_id=int(id))
            Downloader.main()
        else:
            print("Пользователя / группы с таким id не существует")