# SmartLinkViewer API

[![License: BSL v1](https://img.shields.io/badge/License-BSL-1.0-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/Framework-FastAPI-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

Серверная часть системы SmartLink и Neomobile, предоставляющая REST API для взаимодействия с клиентскими данными, ONT (модемами) - в разработке, коробками и вложениями в рамках внутренней системы **Neotelecom**.


##  Возможности

- Получение информации об абоненте
- Поиск абонентов по имени или номеру договора
- Получение вложений клиента и заданий
- Просмотр коробки и соседей
- Авторизация по логину/паролю

## Запуск
```
./scripts/dev.sh #Linux
./scripts/dev.ps1 #Windows
./scripts/prod.sh start #Linux (production)
```
