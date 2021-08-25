<h1 align="center">Скрипт для скачивания фотографий пользователей / групп / бесед ВКонтакте</h1>

<div align="center">
	<a href="https://github.com/YarikMix/vk-admin-bot/vk-photos">
		<img src="https://img.shields.io/github/stars/YarikMix/vk-photos" alt="Stars Badge"/>
	</a>	
</div>


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
token: ""  # Ваш токен (для скачивания фото участников беседы)
```

Запускаем скрипт:
```bash
python vk-photos/main.py
```

Вводим 1, 2, 3 в зависимости от того, чьи фото мы хотим скачать
```bash
>
```

<h2 align="center">(1) Скачать все фото пользователя</h2>

Вводим id пользователя
```bash
> 345691818
```
***Узнать id пользователя или группы ВКонтакте можно [тут](https://regvk.com/id/)***

<h2 align="center">(2) Скачать все фото со стены группы</h2>

Вводим id группы
```bash
> 93933459
```

***Узнать id пользователя или группы ВКонтакте можно [тут](https://regvk.com/id/)***


<h2 align="center">(3) Скачать все фото участников беседы</h2>

Вводим id беседы
```bash
> 136
```

***[Гайд, как узнать id беседы](https://online-vkontakte.ru/2019/01/kak-uznat-id-besedy-v-vk.html)***



После того, как все фотографии скачаются, появится папка 'Фотки' c фотографиями<br><br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/1.png)<br><br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/2.png)<br><br>
![](https://github.com/YarikMix/vk-photos/raw/main/images/3.png)