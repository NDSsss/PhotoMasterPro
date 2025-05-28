# 🎨 PhotoProcessor - AI Photo Editor

Автоматизированный фото-редактор с использованием AI технологий, предоставляющий расширенные инструменты обработки и трансформации изображений.

## ✨ Возможности

- 🖼️ **Удаление фона** - используя rembg и jasperai/LBM_relighting
- 🖼️ **Умная обрезка** - с фокусом на лицах и важных объектах
- 🎭 **Смена людей на фоне** - подстановка людей на разные фоны
- 🖼️ **Добавление рамок** - классические и пользовательские рамки
- 📸 **Создание коллажей** - полароид, сетка, журнальная обложка и др.
- ✨ **Ретушь фотографий** - автоматическое улучшение качества
- 📱 **Оптимизация для соцсетей** - одним кликом для всех платформ
- 🤖 **Telegram бот** - полное зеркало веб-функций
- 🔑 **REST API** - для интеграции с другими приложениями

## 🚀 Быстрый старт

### Режим разработки (с live reload)
```bash
git clone <your-repo>
cd photoprocessor
cp .env.example .env
docker-compose -f docker-compose.dev.yml up --build
```

### Продакшен режим
```bash
docker-compose up --build
```

**Приложение доступно на:** `http://localhost:5000`

## 📚 Документация

- **[Полная инструкция по Docker](DOCKER_SETUP_GUIDE.md)** - подробное руководство
- **[API документация](POSTMAN_TESTING_GUIDE.md)** - тестирование через Postman
- **API Docs:** `http://localhost:5000/api/docs` (после запуска)

## 🛠️ Технологии

- **Backend:** FastAPI, Python 3.11
- **Database:** PostgreSQL + SQLAlchemy
- **AI/ML:** OpenCV, rembg, Pillow
- **Frontend:** Bootstrap 5, JavaScript
- **Bot:** python-telegram-bot
- **Deploy:** Docker, uvicorn

## 🔧 Архитектура

- **Web Interface** - загрузка и обработка через браузер
- **Telegram Bot** - полное зеркало веб-функций
- **REST API** - интеграция с внешними системами
- **JWT Authentication** - безопасная авторизация
- **File Storage** - локальное хранение с организацией

## 📱 Соцсети поддержка

Автоматическая оптимизация для:
- Instagram (пост, stories)
- Facebook (пост, обложка)
- Twitter (пост, header)
- LinkedIn (пост, обложка)
- YouTube (thumbnail, banner)
- TikTok, Pinterest

---

**Готов к использованию!** 🎉