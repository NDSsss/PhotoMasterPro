# 🐳 PhotoProcessor - Локальный запуск с Docker

## 🚀 Быстрый старт

### Предварительные требования
- Docker и Docker Compose установлены на вашей системе
- Минимум 4GB RAM и 10GB свободного места

### 1. Клонирование проекта
```bash
git clone <your-repo-url>
cd photoprocessor
```

### 2. Настройка переменных окружения
```bash
# Скопируйте файл с примером
cp .env.example .env

# Отредактируйте .env файл (опционально)
nano .env
```

### 3. Запуск всего проекта одной командой
```bash
docker-compose up --build
```

**Готово!** 🎉 Приложение будет доступно по адресу: `http://localhost:5000`

## 📋 Что включено

### 🔧 Сервисы
- **PhotoProcessor App** - основное приложение (порт 5000)
- **PostgreSQL** - база данных (порт 5432)
- **Автоматическая инициализация БД** - создание таблиц и демо-данных

### 📁 Постоянные тома
- `uploads/` - загруженные пользователями файлы
- `processed/` - обработанные изображения
- `postgres_data` - данные PostgreSQL

## 🛠️ Полезные команды

### Запуск в фоновом режиме
```bash
docker-compose up -d
```

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Только приложение
docker-compose logs -f app

# Только база данных
docker-compose logs -f postgres
```

### Остановка сервисов
```bash
docker-compose down
```

### Перезапуск с пересборкой
```bash
docker-compose down
docker-compose up --build
```

### Очистка всех данных
```bash
docker-compose down -v
docker system prune -a
```

## 🔍 Проверка работоспособности

### 1. Проверка статуса контейнеров
```bash
docker-compose ps
```

Должно быть:
```
NAME                  STATUS
photoprocessor_app    Up (healthy)
photoprocessor_db     Up (healthy)
```

### 2. Проверка веб-интерфейса
Откройте в браузере: `http://localhost:5000`

### 3. Проверка API
```bash
curl http://localhost:5000/api/docs
```

### 4. Проверка базы данных
```bash
docker-compose exec postgres psql -U photoprocessor -d photoprocessor -c "\dt"
```

## 🎯 Тестирование функций

### Удаление фона через API
```bash
curl -X POST \
  -F "file=@your_image.jpg" \
  -F "method=rembg" \
  http://localhost:5000/api/remove-background \
  --output result.png
```

### Создание пользователя
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}' \
  http://localhost:5000/register
```

## ⚙️ Конфигурация

### Изменение порта приложения
В `docker-compose.yml`:
```yaml
app:
  ports:
    - "8080:5000"  # Приложение будет на порту 8080
```

### Добавление Telegram бота
В `.env` файле:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### Настройка базы данных
В `docker-compose.yml`:
```yaml
postgres:
  environment:
    POSTGRES_DB: your_db_name
    POSTGRES_USER: your_username
    POSTGRES_PASSWORD: your_password
```

## 🐛 Решение проблем

### Проблема: Контейнеры не запускаются
```bash
# Проверьте логи
docker-compose logs

# Освободите порты
sudo lsof -i :5000
sudo lsof -i :5432
```

### Проблема: База данных не инициализируется
```bash
# Удалите том и пересоздайте
docker-compose down -v
docker-compose up --build
```

### Проблема: Недостаточно памяти
```bash
# Увеличьте лимиты в docker-compose.yml
app:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G
```

### Проблема: Медленная обработка изображений
```bash
# Добавьте больше CPU
app:
  deploy:
    resources:
      limits:
        cpus: '2.0'
```

## 🔒 Безопасность

### Изменение паролей в продакшене
В `.env`:
```env
SECRET_KEY=your-super-secure-random-key-here
SESSION_SECRET=another-secure-key-here
POSTGRES_PASSWORD=strong-database-password
```

### Использование secrets в Docker Swarm
```yaml
# docker-compose.prod.yml
secrets:
  db_password:
    external: true
```

## 📊 Мониторинг

### Проверка использования ресурсов
```bash
docker stats
```

### Проверка места на диске
```bash
docker system df
```

### Backup базы данных
```bash
docker-compose exec postgres pg_dump -U photoprocessor photoprocessor > backup.sql
```

### Восстановление базы данных
```bash
docker-compose exec -T postgres psql -U photoprocessor photoprocessor < backup.sql
```

## 🚀 Продакшен

### Создание продакшен-версии
```bash
# Создайте docker-compose.prod.yml
cp docker-compose.yml docker-compose.prod.yml

# Отредактируйте для продакшена
nano docker-compose.prod.yml

# Запуск
docker-compose -f docker-compose.prod.yml up -d
```

### Рекомендации для продакшена
- Используйте внешнюю базу данных
- Настройте SSL/TLS
- Используйте nginx как reverse proxy
- Настройте логирование
- Используйте Docker secrets

## 📞 Поддержка

### Полезные ссылки
- Веб-интерфейс: `http://localhost:5000`
- API документация: `http://localhost:5000/api/docs`
- База данных: `localhost:5432`

### Команды для отладки
```bash
# Подключение к контейнеру приложения
docker-compose exec app bash

# Подключение к базе данных
docker-compose exec postgres psql -U photoprocessor

# Просмотр переменных окружения
docker-compose exec app env
```

---

**🎯 Готово к использованию!** PhotoProcessor полностью настроен и готов к работе в Docker окружении.