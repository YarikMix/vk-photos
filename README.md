## Скрипт для скачивания фотографий пользователей / групп ВКонтакте

[![Github All Releases](https://img.shields.io/github/downloads/YarikMix/vk-photos/total.svg)]()

## Системные требования:

* Python 3 и выше
* Доступ к интернету

## Как использовать:

Скачиваем зависимости:
```bash
pip3 install -r requirements.txt
```

В файл config.yaml вписываем свой логин и пароль от ВКонтакте:
```yaml
login: ""  # Ваш логин он ВКонтакте
password: ""  # Ваш пароль он ВКонтакте
```

Запускаем скрипт:
```bash
python vk-photos/main.py
```

Вводим id пользователя, чьи фотографии хотим скачать.<br>
Для групп вводим id со знаком минус, например -93933459:
```bash
Введите id человека, либо id группы(со знаком минус)
> 345691818
```
Узнать id человека или группы ВКонтакте можно [тут](https://regvk.com/id/)

После того, как все фотографии скачаются, появится папка 'Фотки', в ней будут лежать папки с фотографиями пользователей и групп.
<br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/1.png)
<br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/2.png)
<br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/3.png)