-- ============================================
-- ТЕСТИРОВАНИЕ WORKFLOW "Send Message"
-- ============================================
-- Запуск: docker exec -i n8n-docker-db-1 psql -U n8n_user -d n8n_database -f /home/user/test_send_message_final.sql

-- ============================================
-- ПОДГОТОВКА: Проверка окружения
-- ============================================
SELECT '=== ПРОВЕРКА ОКРУЖЕНИЯ ===' as step;

-- 1. Проверка воркфлоу
SELECT name, active FROM workflow_entity WHERE name = 'Send Message';

-- 2. Проверка telegram_chats
SELECT 'Telegram chats count: ' || COUNT(*) as info FROM telegram_chats;

-- ============================================
-- ЕСЛИ telegram_chats пуст - ДОБАВЬТЕ chat_id
-- ============================================
-- Раскомментируйте и замените YOUR_CHAT_ID на ваш реальный ID
-- INSERT INTO telegram_chats (chat) VALUES ('YOUR_CHAT_ID');

-- ============================================
-- ТЕСТ 1: Прямой INSERT в telegram_send_message
-- ============================================
SELECT '=== ТЕСТ 1: Создание задачи ===' as test;

-- Этот INSERT должен активировать workflow Send Message
INSERT INTO telegram_send_message (chat_id, message) 
VALUES (
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'create_job'
);

-- Проверка
SELECT 'Inserted message: ' || message || ' (ID: ' || id || ')' as result 
FROM telegram_send_message 
ORDER BY id DESC LIMIT 1;

-- ============================================
-- ТЕСТ 2: Начало обработки
-- ============================================
SELECT '=== ТЕСТ 2: Начало обработки ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'start_processing'
);

-- ============================================
-- ТЕСТ 3: Прогресс
-- ============================================
SELECT '=== ТЕСТ 3: Прогресс ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'processing'
);

-- ============================================
-- ТЕСТ 4: Ошибка
-- ============================================
SELECT '=== ТЕСТ 4: Ошибка ===' as test;

-- Примечание: telegram_send_message не имеет поля error_text
-- Ошибка передаётся через payload в реальных сценариях
INSERT INTO telegram_send_message (chat_id, message) 
VALUES (
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'error_processing'
);

-- ============================================
-- ТЕСТ 5: Завершение
-- ============================================
SELECT '=== ТЕСТ 5: Завершение ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'finish_processing'
);

-- ============================================
-- ТЕСТ 6: Остановка (с кнопкой)
-- ============================================
SELECT '=== ТЕСТ 6: Остановка ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'stop_processing'
);

-- ============================================
-- ПРОВЕРКА РЕЗУЛЬТАТОВ
-- ============================================
SELECT '=== ВСЕ СООБЩЕНИЯ ===' as test;

SELECT 
  id,
  chat_id,
  message,
  created_at
FROM telegram_send_message 
ORDER BY id DESC
LIMIT 10;

-- ============================================
-- СТАТИСТИКА
-- ============================================
SELECT '=== СТАТИСТИКА ===' as test;

SELECT 
  message as type,
  COUNT(*) as count,
  MAX(created_at) as last_message
FROM telegram_send_message 
GROUP BY message
ORDER BY message;
