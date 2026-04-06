-- Тестовый скрипт для имитации триггеров n8n
-- Этот скрипт вставляет запись в telegram_send_message, что должно запустить воркфлоу Send Message

-- 1. Тест: Создание задачи
INSERT INTO telegram_send_message (template) VALUES ('create_job');

-- 2. Тест: Процесс перевода (через 5 секунд)
-- INSERT INTO telegram_send_message (template) VALUES ('processing');

-- 3. Тест: Завершение (через 10 секунд)
-- INSERT INTO telegram_send_message (template) VALUES ('finish_processing');
