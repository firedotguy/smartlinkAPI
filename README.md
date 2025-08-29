# SmartLinkViewer API

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/Framework-FastAPI-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

Серверная часть системы SmartLink, предоставляющая REST API для взаимодействия с клиентскими данными, ONT (модемами) - в разработке, коробками и вложениями в рамках внутренней системы **Neotelecom**.

> **Частный проект, лицензирован под GPLv3. Использование в сторонних продуктах запрещено.**


##  Возможности

- Получение информации об абоненте
- Поиск абонентов по имени или номеру договора
- Получение вложений клиента и заданий
- Просмотр коробки и соседей
- Авторизация по логину/паролю

## Запуск
```
pip install -r requirements.txt
uvicorn main:app --host=0.0.0.0
```

## Примеры API

Все ответы содержат:

 - `result`: `OK` или `fail`
 - `api_count`: количество внутренних запросов к UserSide
 - `detail` (только при `result: "fail"`): информация об ошибке


### find `/find?query=QUERY&apikey=APIKEY`
Поиск абонента по имени или номеру договора.

#### Параметры
**query:** Имя или лицевой счет абонента.

#### Ответ
```json
{
  "result": "OK",
  "customers": [
    {
      "id": 123,
      "name": "тест",
      "agreement": "100000"
    }
  ],
  "api_count": 2,
  "search_type": "name"
}
```
### customer `/customer?id=CUSTOMER_ID&apikey=APIKEY`
Получение информации о конкретном абоненте.

#### Параметры
**id:** ID абонента  
_Примечание: Поле geodata может отсутствовать, если координаты и адрес не заданы._
_Примечание 2: Поля `2gis_link` и `neo_link` на старых абонентах могут содержать координаты, а не прямые ссылки (будет исправлено в будущем)_
#### Ответ
```json
{
  "result": "OK",
  "id": 123,
  "api_count": 3,
  "balance": -320,
  "name": "тест",
  "agreement": "100000",
  "status": "Активен",
  "phones": ["+996700123456"],
  "inventory": [
    {
      "id": 1,
      "name": "Huawei ONT",
      "sn": "HW123456789",
      "amount": 1,
      "category_id": 12,
      "catalog_id": 34
    }
  ],
  "house_id": 532,
  "tariffs": [
    {
      "id": 101,
      "name": "Домашний 100"
    }
  ],
  "last_activity": "2024-08-10 13:12:01",
  "group": {
    "id": 5,
    "name": "Тестовая группа"
  },
  "geodata": {
    "coord": [40.12345678, 72.12345678],
    "address": "г. Бишкек, ул. Абая 12",
    "2gis_link": "https://2gis.kg/bishkek/geo/123456",
    "neo_link": "https://neotelecom.kg/map?lat=42.87&lng=74.59"
  },
  "tasks": [
    {
      "id": 123,
      "name": "Подключение Gpon 'частный сектор'",
      "address": "Закирова, 47а",
      "customer_id": 12345,
      "employee_id": 123,
      "dates": {
        "create": "2024-08-20 19:28:53",
        "update": "2024-08-21 14:50:51",
        "complete": "2024-08-21 14:11:51"
      }
    }
  ]
}
```
### box `/box?id=HOUSE_ID&apikey=APIKEY`
Получение информации о доме и соседях.

#### Параметры
**id:** ID коробки

#### Ответ
```json
{
  "result": "OK",
  "api_count": 6,
  "id": 123,
  "building_id": 1234,
  "name": ", ул. Закирова, ФР-074",
  "customers": [
    {
      "id": 456,
      "name": "тест 2",
      "status": "active",
      "last_activity": "2025-07-06 13:12:01",
      "sn": "HW4567890",
      "onu_level": -23.4
    }
  ]
}
```

### attachs `/attachs?id=CUSTOMER_ID&apikey=APIKEY`
Список вложений абонента и его задач.

#### Параметры
**id:** ID абонента

#### Ответ
```json
{
  "result": "OK",
  "api_count": 7,
  "customer": [
    {
      "id": 1,
      "url": "https://us.neotelecom.kg/temporary_attachs/1.png",
      "name": "scan1.png",
      "extension": "png",
      "date": "2025-08-01 12:01:00"
    }
  ],
  "task": [
    {
      "id": 4,
      "url": "https://us.neotelecom.kg/temporary_attachs/4.pdf",
      "name": "report.pdf",
      "extension": "pdf",
      "date": "2025-08-01 12:04:00"
    }
  ]
}
```
### login `/login?login=LOGIN&password=PASS&apikey=APIKEY`
Проверка логина и пароля

#### Параметры
**login:** Проверяемый логин  
**password:** Проверяемый пароль

#### Ответ
```json
{
  "result": "OK",
  "api_count": 1,
  "correct": true
}
```
