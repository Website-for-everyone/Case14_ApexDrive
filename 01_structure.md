# АРХИТЕКТУРА И СПЕЦИФИКАЦИЯ ПРОЕКТА: APEX DRIVE

> **Проект:** Apex Drive — Аренда премиальных спорткаров и трековых суперкаров  
> **Клиент / Заказчик:** Apex Drive Supercar Club (Москва, Moscow Raceway / Сити)  
> **Чек проекта:** 450,000 ₽ | **Срок:** 14 дней (Дедлайн: 2026-11-25)  
> **Дедлайн MVP (80%):** 2026-11-22  
> **Тип договора:** Договор СМЗ с ИП (Чек «Мой Налог»)

---

## 🛠 Технологический стек
- **Frontend / UI:** HTML5 / CSS3 / JavaScript (Telemetry Cockpit SPA), Carbon Fiber Texture, Tachometer Red & Telemetry Green, Web Audio Exhaust Engine Soundboard
- **Backend & Logic:** Python 3.12, FastAPI, Uvicorn, SQLite3, Pydantic v2
- **Telegram Bot:** Aiogram 3.x (Asyncio, FSM, Supercar Fleet Cards, Date Availability, Driver License Photo KYC Intake)
- **Уведомления и лиды:** Автоматическая отправка структурированных заявок владельцу в @Idrisov_prod

---

## 🏛 Архитектурная схема
```
[ Клиент (Web Кокпит) ] ──► [ Телеметрия 0-100 / Звук выхлопа ] ──► [ REST API /api/rentals ] ──┐
                                                                                                  ▼
[ Клиент (Telegram) ] ──► [ Apex Drive Bot (Флот / KYC / Доступность) ] ────────────────► [ SQLite DB ]
                                                                                                  │
                                                                                                  ▼
                                                                                      [ Лиды @Idrisov_prod ]
```

---

## 🔐 Переменные окружения (.env.example)
```env
BOT_TOKEN=8217851677:AAHN34TMuC1P4e6SppuazFN8BIiLHa_RyIc
TELEGRAM_OWNER_ID=1387913438
TELEGRAM_OWNER_USERNAME=@Idrisov_prod
PORT=3014
API_PORT=8014
PROXY_URL=socks5://dsZwtR:PTJNnz@72.57.96.136:8000
DATABASE_PATH=apexdrive.db
```

---

## 🔗 Ресурсы и ссылки
- **Порт Web UI / API:** `http://localhost:3014` / `http://localhost:8014`
- **Telegram Bot:** `@ApexDriveRentBot`
- **Канал заявок:** `@Idrisov_prod`
