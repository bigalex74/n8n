-- ============================================
-- НАСТРОЙКА ТЕСТИРОВАНИЯ
-- ============================================

-- ============================================
-- ШАГ 1: Добавьте ваш Telegram chat_id
-- ============================================
-- 1. Откройте бота @userinfobot в Telegram
-- 2. Нажмите Start
-- 3. Скопируйте ваш ID (например: 123456789)
-- 4. Вставьте вместо YOUR_CHAT_ID ниже:

INSERT INTO telegram_chats (chat) 
VALUES ('YOUR_CHAT_ID')  -- <-- ЗАМЕНИТЕ НА ВАШ ID
ON CONFLICT (chat) DO NOTHING;

-- Проверка
SELECT * FROM telegram_chats;

-- ============================================
-- ШАГ 2: Создайте тестовую задачу
-- ============================================
INSERT INTO document_jobs (
  file_name, 
  status, 
  billing_polza, 
  billing_neuro, 
  translated_file,
  created_at
) VALUES (
  'Тестовый документ.pdf',
  'pending',
  '100.50',
  '50.25',
  'Тестовый документ_ru.pdf',
  NOW() - INTERVAL '1 hour'
)
RETURNING id;

-- Активация задачи
INSERT INTO job_current (job_id, current_arc, count_done_chunks, error_text, count_error_chunks) 
VALUES (
  (SELECT id FROM document_jobs WHERE file_name = 'Тестовый документ.pdf' ORDER BY id DESC LIMIT 1),
  1,
  5,
  NULL,
  0
)
ON CONFLICT (job_id) DO UPDATE SET 
  current_arc = 1,
  count_done_chunks = 5,
  error_text = NULL,
  count_error_chunks = 0;

-- ============================================
-- ШАГ 3: Создайте тестовые чанки
-- ============================================
-- 10 чанков, 5 готовых
INSERT INTO document_chunks (job_id, chunk_index, status, text) 
SELECT 
  (SELECT id FROM document_jobs WHERE file_name = 'Тестовый документ.pdf' ORDER BY id DESC LIMIT 1),
  i,
  CASE WHEN i <= 5 THEN 'done' ELSE 'pending' END,
  'Тестовый текст чанка ' || i
FROM generate_series(1, 10) AS i
ON CONFLICT (job_id, chunk_index) DO UPDATE SET 
  status = EXCLUDED.status,
  text = EXCLUDED.text;

-- Проверка
SELECT 
  job_id,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'done') as done
FROM document_chunks 
GROUP BY job_id;

-- ============================================
-- ШАГ 4: ТЕСТОВЫЕ СЦЕНАРИИ
-- ============================================
-- Запускайте по одному и проверяйте Telegram

-- ТЕСТ 1: Создание задачи (🆕)
INSERT INTO telegram_send_message (chat_id, message, type) 
SELECT 
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'create_job',
  'create';

-- ТЕСТ 2: Начало обработки (▶️)
INSERT INTO telegram_send_message (chat_id, message, type) 
SELECT 
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'start_processing',
  'start';

-- ТЕСТ 3: Прогресс (🔄)
INSERT INTO telegram_send_message (chat_id, message, type) 
SELECT 
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'processing',
  'process';

-- ТЕСТ 4: Ошибка (⚠️)
INSERT INTO telegram_send_message (chat_id, message, type, error_text) 
SELECT 
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'error_processing',
  'error',
  'Тестовая ошибка: API timeout';

-- ТЕСТ 5: Завершение (✅)
-- Сначала обновим задачу
UPDATE document_jobs SET finished_at = NOW() WHERE file_name = 'Тестовый документ.pdf';
UPDATE document_chunks SET status = 'done' WHERE job_id = (SELECT id FROM document_jobs WHERE file_name = 'Тестовый документ.pdf');

INSERT INTO telegram_send_message (chat_id, message, type) 
SELECT 
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'finish_processing',
  'finish';

-- ТЕСТ 6: Остановка с кнопкой (🚨)
INSERT INTO telegram_send_message (chat_id, message, type) 
SELECT 
  (SELECT chat::bigint FROM telegram_chats LIMIT 1),
  'stop_processing',
  'stop';

-- ============================================
-- ПРОВЕРКА РЕЗУЛЬТАТОВ
-- ============================================
SELECT 
  id,
  chat_id,
  message,
  type,
  status,
  message_id,
  created_at
FROM telegram_send_message 
ORDER BY id DESC
LIMIT 10;

-- ============================================
-- ОЧИСТКА (после тестирования)
-- ============================================
-- DELETE FROM telegram_send_message WHERE chat_id = (SELECT chat::bigint FROM telegram_chats LIMIT 1);
-- DELETE FROM document_chunks WHERE job_id = (SELECT id FROM document_jobs WHERE file_name = 'Тестовый документ.pdf');
-- DELETE FROM job_current WHERE job_id = (SELECT id FROM document_jobs WHERE file_name = 'Тестовый документ.pdf');
-- DELETE FROM document_jobs WHERE file_name = 'Тестовый документ.pdf';
