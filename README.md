<h1 align="center">Скрипт для скачивания фотографий пользователей / групп ВКонтакте </h1>

<a href="https://github.com/YarikMix/vk-admin-bot/vk-photos" style="margin: auto;">
	<img src="https://img.shields.io/github/stars/YarikMix/vk-photos" alt="Stars Badge"/>
</a>

### Системные требования:

* Python 3 и выше
* Доступ к интернету
* Логин и пароль от ВКонтакте

### Как использовать:

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

Вводим id пользователя, чьи фотографии хотим скачать<br>
Для групп вводим id со знаком минус, например -93933459:
```bash
Введите id человека, либо id группы(со знаком минус)
> 
```

Узнать id человека или группы ВКонтакте можно [тут](https://regvk.com/id/)

После того, как все фотографии скачаются, появится папка 'Фотки' c фотографиями<br><br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/1.png)<br><br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/2.png)<br><br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/3.png)