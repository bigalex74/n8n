# Инструкция по использованию pgAdmin для n8n PostgreSQL

## 📋 Описание

pgAdmin — веб-интерфейс для администрирования PostgreSQL базы данных n8n.

## 🚀 Быстрый старт

### 1. Настройка (выполняется один раз)

```bash
cd ~/n8n-docker
./setup_pgadmin.sh
```

### 2. Запуск pgAdmin

```bash
./start_pgadmin.sh
```

### 3. Открыть в браузере

Перейдите по адресу: **http://localhost:5050/browser/**

> 💡 **Если подключаетесь по SSH:** используйте SSH-туннель
> ```bash
> ssh -L 5050:localhost:5050 user@bigalexn8n.ru
> ```
> Затем откройте `http://localhost:5050` в браузере на вашем компьютере.
> 
> Или используйте ярлык **🔗 SSH-туннель pgAdmin** на рабочем столе.

### 4. Вход в систему

- **Email:** `admin@admin.com`
- **Пароль:** `admin`

## 🔌 Подключение к PostgreSQL n8n

После входа в pgAdmin:

1. Нажмите правой кнопкой на **Servers** → **Register** → **Server**
2. Вкладка **General**:
   - Name: `n8n PostgreSQL`
3. Вкладка **Connection**:
   - Host name/address: `db`
   - Port: `5432`
   - Maintenance database: `n8n_database`
   - Username: `n8n_user`
   - Password: `n8n_db_password`
4. Нажмите **Save**

## 📊 Параметры подключения

| Параметр | Значение |
|----------|----------|
| Host | `db` |
| Port | `5432` |
| Database | `n8n_database` |
| Username | `n8n_user` |
| Password | `n8n_db_password` |

## ⏹️ Остановка pgAdmin

```bash
./stop_pgadmin.sh
```

## 🔄 Перезапуск pgAdmin

```bash
./stop_pgadmin.sh
./start_pgadmin.sh
```

## 📁 Расположение файлов

| Файл | Описание |
|------|----------|
| `setup_pgadmin.sh` | Настройка (добавляет pgAdmin в docker-compose) |
| `start_pgadmin.sh` | Запуск pgAdmin |
| `stop_pgadmin.sh` | Остановка pgAdmin |
| `docker-compose.yml` | Конфигурация Docker (обновляется setup скриптом) |

## 🔐 Безопасность

> ⚠️ **Важно:** pgAdmin запущен с параметром `SERVER_MODE=False`, что означает:
> - Доступен только локально (localhost:5050)
> - Не требует мастер-пароля
> - **Не рекомендуется** открывать доступ извне без дополнительной настройки

### Для продакшена измените:

1. В `docker-compose.yml` уберите порт или настройте reverse proxy
2. Установите сложный пароль в `.env`:
   ```bash
   PGADMIN_DEFAULT_PASSWORD=ваш_сложный_пароль
   ```

## 🛠️ Полезные команды

```bash
# Статус pgAdmin
sudo docker ps --filter "name=pgadmin"

# Логи pgAdmin
sudo docker logs n8n-docker-pgadmin-1

# Перезапуск контейнера
sudo docker restart n8n-docker-pgadmin-1

# Полное удаление (с потерей данных)
sudo docker compose down pgadmin
sudo docker volume rm n8n-docker_pgadmin_data
```

## 📊 Что можно делать в pgAdmin

- ✅ Просмотр таблиц и данных
- ✅ Выполнение SQL-запросов (Query Tool)
- ✅ Создание/изменение таблиц
- ✅ Управление пользователями и правами
- ✅ Резервное копирование и восстановление
- ✅ Мониторинг производительности

## ❓ Troubleshooting

### pgAdmin не запускается
```bash
# Проверьте логи
sudo docker logs n8n-docker-pgadmin-1

# Пересоздайте контейнер
sudo docker compose up -d --force-recreate pgadmin
```

### Не подключается к PostgreSQL
- Убедитесь, что PostgreSQL запущен: `sudo docker ps | grep db`
- Проверьте, что pgAdmin в той же сети: `sudo docker network inspect n8n-docker_n8n-network`

### Забыли пароль pgAdmin
Измените в `docker-compose.yml` и перезапустите:
```bash
PGADMIN_DEFAULT_PASSWORD=новый_пароль
```
