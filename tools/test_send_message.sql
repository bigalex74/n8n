-- ============================================
-- ТЕСТОВЫЕ СЦЕНАРИИ ДЛЯ Send Message WORKFLOW
-- ============================================
-- Описание: Скрипт для тестирования воркфлоу "Send Message"
-- Использование: Запускайте тесты последовательно и проверяйте 
--                сообщения в вашем Telegram чате
-- ============================================

-- ============================================
-- ПОДГОТОВКА: Проверка структуры таблиц
-- ============================================
-- document_jobs: id, file_name, status, billing_polza, billing_neuro, ...
-- telegram_send_message: id, chat_id, message, created_at
-- job_current: job_id (FK на document_jobs.id)
-- document_chunks: id, job_id, chunk_index, status

-- ============================================
-- СОЗДАНИЕ ТЕСТОВОЙ ЗАДАЧИ
-- ============================================
-- Используем существующую задачу или создаём новую
SELECT '=== ПОДГОТОВКА: Поиск тестовой задачи ===' as test;

-- Проверяем есть ли активная задача
SELECT jc.job_id, dj.id, dj.file_name, dj.status
FROM job_current jc
JOIN document_jobs dj ON jc.job_id = dj.id
LIMIT 1;

-- Если нет активной задачи, используем job_id = 1 для тестов
-- или создаём новую запись (раскомментировать при необходимости)
/*
INSERT INTO document_jobs (file_name, status, billing_polza, billing_neuro) 
VALUES ('Test Document.pdf', 'pending', '100.50', '50.25')
RETURNING id;

INSERT INTO job_current (job_id) VALUES (LASTVAL());
*/

-- Для тестов используем существующую задачу
-- ЗАМЕНИТЕ 1 на актуальный job_id из вашей системы
\set TEST_JOB_ID 1

-- ============================================
-- ПОДГОТОВКА: Создание тестовых чанков
-- ============================================
SELECT '=== ПОДГОТОВКА: Создание тестовых чанков ===' as test;

-- Создаём 10 чанков (5 готовых, 5 в процессе)
INSERT INTO document_chunks (job_id, chunk_index, status) 
SELECT :TEST_JOB_ID, i, CASE WHEN i <= 5 THEN 'done' ELSE 'pending' END
FROM generate_series(1, 10) AS i
ON CONFLICT (job_id, chunk_index) DO UPDATE SET status = EXCLUDED.status;

-- Проверка чанков
SELECT 
  job_id,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'done') as done,
  COUNT(*) FILTER (WHERE status = 'pending') as pending
FROM document_chunks 
WHERE job_id = :TEST_JOB_ID
GROUP BY job_id;

-- ============================================
-- ТЕСТ 1: Создание задачи
-- ============================================
-- Ожидаемое сообщение: "🆕 Задача создана"
SELECT '=== ТЕСТ 1: Создание задачи ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (
  0,  -- placeholder, будет заменено на реальный chat_id из telegram_chats
  'create_job'
);

-- Проверка: сообщение создано
SELECT COUNT(*) as test_1_count FROM telegram_send_message WHERE message = 'create_job';

-- ============================================
-- ТЕСТ 2: Начало обработки
-- ============================================
-- Ожидаемое сообщение: "▶️ Обработка началась"
SELECT '=== ТЕСТ 2: Начало обработки ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (0, 'start_processing');

-- Проверка: должно быть 2 сообщения
SELECT COUNT(*) as test_2_count FROM telegram_send_message WHERE message IN ('create_job', 'start_processing');

-- ============================================
-- ТЕСТ 3: Прогресс (5 из 10 чанков)
-- ============================================
-- Ожидаемое сообщение: "🔄 Перевод в процессе" с прогресс-баром 50%
SELECT '=== ТЕСТ 3: Прогресс ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (0, 'processing');

-- Проверка: должно быть 3 сообщения
SELECT COUNT(*) as test_3_count FROM telegram_send_message WHERE message IN ('create_job', 'start_processing', 'processing');

-- ============================================
-- ТЕСТ 4: Ошибка
-- ============================================
-- Ожидаемое сообщение: "⚠️ Ошибка обработки"
-- Примечание: telegram_send_message не имеет поля error_text
-- Ошибка передаётся через message или в payload
SELECT '=== ТЕСТ 4: Ошибка ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (0, 'error_processing');

-- Проверка: должно быть 4 сообщения
SELECT COUNT(*) as test_4_count FROM telegram_send_message WHERE message IN ('create_job', 'start_processing', 'processing', 'error_processing');

-- ============================================
-- ТЕСТ 5: Завершение
-- ============================================
-- Ожидаемое сообщение: "✅ Перевод завершен!" с итогами
SELECT '=== ТЕСТ 5: Завершение ===' as test;

UPDATE document_jobs SET finished_at = NOW() WHERE id = :TEST_JOB_ID;
UPDATE document_chunks SET status = 'done' WHERE job_id = :TEST_JOB_ID;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (0, 'finish_processing');

-- Проверка: должно быть 5 сообщений
SELECT COUNT(*) as test_5_count FROM telegram_send_message WHERE message IN ('create_job', 'start_processing', 'processing', 'error_processing', 'finish_processing');

-- ============================================
-- ТЕСТ 6: Остановка (с кнопкой)
-- ============================================
-- Ожидаемое сообщение: "🚨 Перевод остановлен" + кнопка "🔁 Повторить"
SELECT '=== ТЕСТ 6: Остановка ===' as test;

INSERT INTO telegram_send_message (chat_id, message) 
VALUES (0, 'stop_processing');

-- Проверка: должно быть 6 сообщений
SELECT COUNT(*) as test_6_count FROM telegram_send_message WHERE message IN ('create_job', 'start_processing', 'processing', 'error_processing', 'finish_processing', 'stop_processing');

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
-- ФИНАЛЬНАЯ СТАТИСТИКА
-- ============================================
SELECT '=== ФИНАЛЬНАЯ СТАТИСТИКА ===' as test;

SELECT 
  message as type,
  COUNT(*) as count,
  MAX(created_at) as last_message
FROM telegram_send_message 
GROUP BY message
ORDER BY message;

-- ============================================
-- ОЧИСТКА (раскомментировать после тестирования)
-- ============================================
-- DELETE FROM telegram_send_message WHERE message IN ('create_job', 'start_processing', 'processing', 'error_processing', 'finish_processing', 'stop_processing');
-- DELETE FROM document_chunks WHERE job_id = :TEST_JOB_ID;
