# Телеграм Бот для Яндекс Практикума

## Описание

Этот Телеграм бот уведомляет вас об изменениях в статусе проверки домашнего задания на сервисе Яндекс Практикум. Он отправляет запросы к API Яндекс Домашка и, обнаружив изменения, уведомляет вас в чате Телеграм.

## Возможности

- Отправка сообщений о статусе проверки домашних заданий.
- Обработка ошибок для обеспечения стабильной работы.
- Логирование работы функций для отслеживания и отладки.

## Технологии

- Python
- pyTelegramBotAPI

## Установка

-- Требования

- Python 3.x
- Телеграм аккаунт
- Токен для доступа к вашему боту от BotFather
- Токен для доступа к API Яндекс Домашки

-- Шаги

1. Клонируйте репозиторий:

   
```
   git clone https://github.com/ваш-аккаунт/yandex-practikum-bot.git
   cd yandex-practikum-bot
```
   

2. Создайте и активируйте виртуальное окружение:

   
```
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
```   

3. Установите зависимости:

   
```
   pip install -r requirements.txt
```

4. Настройте переменные окружения:

   Создайте файл .env и добавьте в него ваши токены:

```   
   PRACTICUM_TOKEN=ваш_токен_яндекс_практикум
   TELEGRAM_TOKEN=ваш_токен_телеграм_бота
   CHAT_ID=ваш_чат_id
```
   

5. Запустите бота:

   
```
   python main.py
```

## Использование

- Бот автоматически отправляет уведомления, как только обнаруживает изменения в статусе проверки.

## Демонстрация

![image](https://github.com/user-attachments/assets/d9bfe728-cca1-4998-babd-9445d599a21f)

## Ссылка на бота
Телеграм - @HomePracticumYaBot

