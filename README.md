# SmartLink API

[![License: BSL v1](https://img.shields.io/badge/License-BSL_v1.0-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](www.python.org) ![FastAPI](https://img.shields.io/badge/Framework-FastAPI-green)

Серверная часть системы [SmartLink](https://github.com/firedotguy/smartlink) и Neomobile, предоставляющая REST API для взаимодействия с клиентскими данными, ONT, заданиях и т.д. в рамках внутренней системы **Neotelecom**.

## Планы

...
 - [x] Подключение к ONT через SSH
 - [ ] Автообновление кэша каждый день
 - [ ] Логирование
 - [ ] Разделенное получения данных по абоненту
 - [ ] Передача параметров API UserSide через kwargs вместо строки
 - [ ] Все cat & action из UserSide для полной импортозамещаемости

...

## Запуск
```bash
./scripts/dev.sh #Linux
./scripts/dev.ps1 #Windows
./scripts/prod.sh start #Linux (production)
```
