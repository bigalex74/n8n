# Инструкция по настройке прокси для Telegram в n8n

## ❌ Проблема

Telegram API заблокирован на уровне провайдера/сервера. Прямое подключение невозможно.

## ✅ Решение

Использовать HTTP/HTTPS прокси для подключения к Telegram API.

---

## Вариант 1: Бесплатные прокси (для теста)

**Список бесплатных прокси:**
- https://free-proxy-list.net/
- https://www.proxy-list.download/
- https://openproxy.space/

**Как использовать:**

1. Найдите рабочий прокси (HTTP/HTTPS, порт 80/443/8080)
2. Откройте `docker-compose.yml`
3. Раскомментируйте и заполните:
   ```yaml
   environment:
     - HTTP_PROXY=http://123.45.67.89:8080
     - HTTPS_PROXY=http://123.45.67.89:8080
   ```
4. Перезапустите n8n:
   ```bash
   cd /home/user/n8n-docker
   sudo docker compose up -d n8n
   ```
5. Проверьте:
   ```bash
   sudo docker exec n8n-docker-n8n-1 node -e "
   const https = require('https');
   https.get('https://api.telegram.org/botTOKEN/getMe', (res) => {
     console.log('Status:', res.statusCode);
   }).on('error', console.error);
   "
   ```

**⚠️ Минусы:**
- Нестабильные (работают несколько часов/дней)
- Медленные
- Могут воровать данные

---

## Вариант 2: Платные прокси (рекомендуется)

**Сервисы:**
| Сервис | Цена | Ссылка |
|--------|------|--------|
| IPRoyal | от $3/мес | https://iproyal.com/ |
| Smartproxy | от $7/мес | https://smartproxy.com/ |
| Bright Data | от $15/мес | https://brightdata.com/ |
| Proxy-Seller | от $2/мес | https://proxy-seller.com/ |

**Как настроить:**

1. Купите прокси (HTTP/HTTPS)
2. Получите доступы (IP:port:user:pass)
3. Откройте `docker-compose.yml`
4. Добавьте:
   ```yaml
   environment:
     - HTTP_PROXY=http://user:pass@proxy-ip:port
     - HTTPS_PROXY=http://user:pass@proxy-ip:port
   ```
5. Перезапустите:
   ```bash
   cd /home/user/n8n-docker
   sudo docker compose up -d n8n
   ```

---

## Вариант 3: Свой прокси на VPS

**Если есть VPS в другой стране:**

1. Подключитесь к VPS
2. Установите 3proxy:
   ```bash
   apt update && apt install -y 3proxy
   ```
3. Настройте `/etc/3proxy/3proxy.cfg`:
   ```
   auth none
   allow *
   proxy -p8080
   ```
4. Запустите:
   ```bash
   systemctl start 3proxy
   ```
5. Используйте `http://vps-ip:8080` в n8n

---

## Вариант 4: Использовать альтернативы Telegram

**Если прокси не подходит:**

### Email уведомления
- Используйте ноду **Email Send**
- Настройте SMTP (Gmail, Yandex, etc.)

### Discord webhook
- Создайте webhook в Discord сервере
- Используйте **HTTP Request** ноду

### Slack
- Используйте официальную ноду **Slack**

### Pushover
- Сервис push-уведомлений
- https://pushover.net/

---

## Проверка работы

После настройки прокси:

```bash
# Проверка из контейнера n8n
sudo docker exec n8n-docker-n8n-1 node -e "
const https = require('https');
const options = {
  hostname: 'api.telegram.org',
  path: '/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/getMe'
};
https.get(options, (res) => {
  console.log('✅ Telegram API:', res.statusCode);
}).on('error', (e) => console.log('❌ Error:', e.message));
"
```

**Ожидаемый результат:**
```json
{"ok":true,"result":{"id":8591497428,"is_bot":true,"first_name":"...","username":"..."}}
```

---

## Настройка в n8n

После того как прокси работает:

1. Откройте https://bigalexn8n.ru/
2. Создайте credentials для Telegram:
   - Type: Telegram API
   - Token: `8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0`
3. Создайте workflow с **Telegram Trigger**
4. Активируйте workflow

---

## Troubleshooting

### Прокси не работает

1. Проверьте прокси вручную:
   ```bash
   curl -x http://proxy:port https://api.telegram.org/
   ```
2. Попробуйте другой прокси
3. Проверьте firewall

### Ошибка SSL

Добавьте в `docker-compose.yml`:
```yaml
environment:
  - NODE_TLS_REJECT_UNAUTHORIZED=0
```

### Таймауты

Увеличьте таймаут в настройках ноды Telegram:
- Timeout: 30000 (30 секунд)
- Retry on fail: true
