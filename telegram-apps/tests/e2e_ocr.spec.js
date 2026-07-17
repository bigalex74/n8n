const { test, expect } = require('@playwright/test');

test('OCR screen shows authenticated production status and safe launch flow', async ({ page }) => {
  const initData = process.env.OCR_E2E_INIT_DATA;
  if (!initData) throw new Error('OCR_E2E_INIT_DATA is required');

  await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: `window.Telegram = { WebApp: {
        initData: ${JSON.stringify(initData)},
        ready() {}, expand() {},
        BackButton: { show() {}, onClick() {} },
        HapticFeedback: { notificationOccurred() {} },
        showConfirm(_text, callback) { callback(true); }
      }};`,
    });
  });

  let startCalled = false;
  await page.route('**/api/ocr/start', async route => {
    startCalled = true;
    await route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({ accepted: true, message: 'OCR batch accepted' }),
    });
  });

  await page.goto('/ocr');
  await expect(page.getByRole('heading', { name: 'OCR изображений' })).toBeVisible();
  await expect(page.locator('#serviceStatus')).toContainText(/готов/i);
  await expect(page.locator('#sourceFolder')).toHaveText('протокол');
  await expect(page.getByRole('button', { name: 'Запустить OCR' })).toBeEnabled();

  await page.getByRole('button', { name: 'Запустить OCR' }).click();
  await expect.poll(() => startCalled).toBe(true);
  await expect(page.locator('#message')).toContainText('Запуск принят');
});

test('OCR screen blocks a browser opened outside Telegram', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: 'window.Telegram = { WebApp: { initData: "", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} } } };',
    });
  });
  await page.goto('/ocr');
  await expect(page.getByRole('button', { name: 'Запустить OCR' })).toBeDisabled();
  await expect(page.locator('#message')).toContainText('Откройте приложение через Telegram');
});

test('OCR screen renders live progress without Telegram message fan-out', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, showConfirm(_text, callback) { callback(true); } } };',
    });
  });
  await page.route('**/api/ocr/status', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
          source_folder: 'протокол',
          service: { ready: true },
          can_start: false,
          can_stop: true,
        batch: {
          status: 'running', started_at: '2026-07-16T10:00:00Z',
          progress_total: 121, progress_completed: 60,
          progress_failed: 1, progress_current_file: '161.png',
        },
      }),
    });
  });
  let stopCalled = false;
  await page.route('**/api/ocr/stop', async route => {
    stopCalled = true;
    await route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ accepted: true }) });
  });

  await page.goto('/ocr');
  await expect(page.locator('#progressPanel')).toBeVisible();
  await expect(page.locator('#progressPercent')).toHaveText('50%');
  await expect(page.locator('#progressDetail')).toContainText('61 из 121');
  await expect(page.locator('#progressDetail')).toContainText('161.png');
  await expect(page.getByRole('button', { name: 'Запустить OCR' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Остановить OCR' })).toBeVisible();
  await page.getByRole('button', { name: 'Остановить OCR' }).click();
  await expect.poll(() => stopCalled).toBe(true);
  await expect(page.locator('#message')).toContainText('Останавливаю');
});

test('OCR screen reprocesses selected images only', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, showConfirm(_text, callback) { callback(true); } } };',
    });
  });
  await page.route('**/api/ocr/status', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ source_folder: 'протокол', service: { ready: true }, can_start: true, can_stop: false, batch: { status: 'done' } }),
  }));
  await page.route('**/api/ocr/files', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ files: [
      { source_name: '106.png', status: 'done', quality: 'ok', quality_label: 'распознано' },
      { source_name: '145.png', status: 'done', quality: 'warning', quality_label: 'нужна проверка' },
      { source_name: '222.png', status: 'new', quality: 'unrecognized', quality_label: 'не обработано' },
    ] }),
  }));
  let requestedFiles = null;
  await page.route('**/api/ocr/start', async route => {
    requestedFiles = (await route.request().postDataJSON()).force_files;
    await route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ accepted: true }) });
  });

  await page.goto('/ocr');
  await page.getByRole('tab', { name: 'Повторно' }).click();
  await expect(page.getByText('106.png').locator('..')).toHaveAttribute('data-quality', 'ok');
  await expect(page.getByText('145.png').locator('..')).toHaveAttribute('data-quality', 'warning');
  await expect(page.getByText('222.png').locator('..')).toHaveAttribute('data-quality', 'unrecognized');
  await page.getByText('106.png').click();
  await page.getByRole('button', { name: /Повторить OCR для 1/ }).click();
  await expect.poll(() => requestedFiles).toEqual(['106.png']);
});

test('OCR screen selects all, clears selection and requests TXT deletion safely', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, HapticFeedback: { notificationOccurred() {} }, showConfirm(_text, callback) { callback(true); } } };',
  }));
  await page.route('**/api/ocr/status', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ source_folder: 'протокол', service: { ready: true }, can_start: true, can_stop: false, batch: { status: 'done' } }),
  }));
  await page.route('**/api/ocr/files', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ files: [
      { source_name: '101.png', status: 'done', quality: 'ok', quality_label: 'распознано' },
      { source_name: '102.png', status: 'done', quality: 'warning', quality_label: 'нужна проверка' },
      { source_name: '103.png', status: 'new', quality: 'unrecognized', quality_label: 'не обработано' },
    ] }),
  }));
  let deleteBody = null;
  await page.route('**/api/ocr/delete-txt', async route => {
    deleteBody = await route.request().postDataJSON();
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ deleted_count: 2, moved_to_trash: true }),
    });
  });

  await page.goto('/ocr');
  await page.getByRole('tab', { name: 'Повторно' }).click();
  await page.getByRole('button', { name: 'Выделить все' }).click();
  await expect(page.locator('#fileList input:checked')).toHaveCount(3);
  await expect(page.getByRole('button', { name: /Повторить OCR для 3/ })).toBeEnabled();
  await page.getByRole('button', { name: 'Снять' }).click();
  await expect(page.locator('#fileList input:checked')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Повторить OCR' })).toBeDisabled();
  await page.getByText('Опасная зона').click();
  await page.getByRole('button', { name: 'Переместить TXT в Корзину' }).click();
  await expect.poll(() => deleteBody).toEqual({ confirmation: 'DELETE_ALL_OCR_TXT' });
  await expect(page.locator('#message')).toContainText('Удалено TXT: 2');
});

test('OCR screen merges current TXT in filename order and confirms Telegram delivery', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, HapticFeedback: { notificationOccurred() {} }, showConfirm(_text, callback) { callback(true); } } };',
  }));
  await page.route('**/api/ocr/status', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ source_folder: 'протокол', service: { ready: true }, can_start: true, can_stop: false, batch: { status: 'done' } }),
  }));
  await page.route('**/api/ocr/files', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ files: [
      { source_name: '1.png', status: 'done', quality: 'ok', quality_label: 'без автопредупреждений', output_exists: true },
      { source_name: '2.png', status: 'done', quality: 'ok', quality_label: 'без автопредупреждений', output_exists: true },
    ] }),
  }));
  let mergeBody = null;
  await page.route('**/api/ocr/merge-txt', async route => {
    mergeBody = await route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      output_name: 'ocr_merged.txt', source_count: 2, size: 18, sha256: 'verified',
      verified: true, delivered_to_telegram: true, telegram_message_id: 456,
    }) });
  });

  await page.goto('/ocr');
  await page.getByRole('button', { name: 'Объединить 2 TXT' }).click();
  await expect.poll(() => mergeBody).toEqual({ confirmation: 'MERGE_CURRENT_OCR_TXT' });
  await expect(page.locator('#mergeResult')).toContainText('Файл отправлен в этот чат');
  await expect(page.locator('#message')).toContainText('отправлен в чат');
});

test('OCR screen filters current files by recognition status', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} } } };',
  }));
  await page.route('**/api/ocr/status', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ source_folder: 'протокол', service: { ready: true }, can_start: true, can_stop: false, batch: { status: 'done' } }),
  }));
  await page.route('**/api/ocr/files', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ files: [
      { source_name: '101.png', status: 'done', quality: 'ok', quality_label: 'распознано' },
      { source_name: '102.png', status: 'done', quality: 'warning', quality_label: 'нужна проверка' },
      { source_name: '103.png', status: 'new', quality: 'unrecognized', quality_label: 'не обработано' },
      { source_name: '104.png', status: 'processing', quality: 'processing', quality_label: 'обрабатывается' },
    ] }),
  }));

  await page.goto('/ocr');
  await page.getByRole('tab', { name: 'Повторно' }).click();
  await expect(page.locator('#fileList .file-item')).toHaveCount(4);
  await expect(page.locator('#filterCount')).toHaveText('4 из 4');

  await page.locator('#statusFilter').selectOption('warning');
  await expect(page.locator('#fileList .file-item')).toHaveCount(1);
  await expect(page.getByText('102.png')).toBeVisible();
  await expect(page.locator('#filterCount')).toHaveText('1 из 4');

  await page.getByRole('button', { name: 'Выделить все' }).click();
  await expect(page.locator('#fileList input:checked')).toHaveCount(1);
  await page.locator('#statusFilter').selectOption('unrecognized');
  await expect(page.locator('#fileList input:checked')).toHaveCount(0);
  await expect(page.getByText('103.png')).toBeVisible();
});

test('OCR screen selects AI model and sends edited prompt', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, showConfirm(_text, callback) { callback(true); } } };',
  }));
  await page.route('**/api/ocr/config', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      ai_models: [
        { id: 'gpt-5.6-luna', label: 'Luna — быстро' },
        { id: 'gpt-5.6-terra', label: 'Terra — баланс' },
        { id: 'gpt-5.6-sol', label: 'Sol — качество' },
      ],
      default_ai_model: 'gpt-5.6-luna',
      default_ai_prompt: 'Исходный промпт распознавания корейского текста без перевода.',
    }),
  }));
  await page.route('**/api/ocr/status', async route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({
      source_folder: 'протокол',
      service: { ready: true },
      services: { paddle: { ready: true }, ai: { ready: true } },
      can_start: true, can_stop: false, batch: { status: 'done', ocr_engine: 'paddle' },
    }),
  }));
  await page.route('**/api/ocr/files', async route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ files: [] }),
  }));
  let requestBody = null;
  await page.route('**/api/ocr/start', async route => {
    requestBody = await route.request().postDataJSON();
    await route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ accepted: true }) });
  });

  await page.goto('/ocr');
  await page.getByText('Настройки распознавания').click();
  await page.locator('#engineSelect').selectOption('ai');
  await page.locator('#modelSelect').selectOption('gpt-5.6-terra');
  await page.locator('#promptInput').fill('Мой точный промпт: сохранить строки, кавычки и многоточия без перевода.');
  await page.getByRole('button', { name: 'Запустить OCR' }).click();

  await expect.poll(() => requestBody && requestBody.engine).toBe('ai');
  expect(requestBody.model).toBe('gpt-5.6-terra');
  expect(requestBody.prompt).toContain('сохранить строки');
});

test('OCR review keeps baseline separate and publishes only after confirmation', async ({ page }) => {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, showConfirm(_text, callback) { callback(true); } } };',
  }));
  await page.route('**/api/ocr/config', async route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ ai_models: [], default_ai_prompt: 'Распознай корейский текст точно, без перевода и домыслов.' }),
  }));
  await page.route('**/api/ocr/status', async route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ source_folder: 'протокол', service: { ready: true }, can_start: true, can_stop: false, batch: { status: 'done' } }),
  }));
  await page.route('**/api/ocr/files', async route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify({ files: [
      { source_name: '145.png', status: 'done', quality: 'warning', quality_label: 'нужна проверка', output_exists: true },
    ] }),
  }));
  let reviews = [];
  await page.route('**/api/ocr/reviews', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ reviews }) });
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/ocr/reviews/candidate', async route => {
    reviews = [{
      id: 1, source_name: '145.png', status: 'candidate_ready', model: 'gpt-5.6-terra',
      baseline_text: '안녕 f1...', candidate_text: '안녕...', decision_reason: 'артефакт устранён',
      source_url: 'https://example.test/145.png',
      diff_json: { diff: ['-안녕 f1...', '+안녕...'] },
    }];
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ review: reviews[0] }) });
  });
  let accepted = false;
  await page.route('**/api/ocr/reviews/1/action', async route => {
    accepted = (await route.request().postDataJSON()).action === 'accept';
    reviews[0].status = 'accepted';
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ review: reviews[0] }) });
  });

  await page.goto('/ocr');
  await page.getByRole('tab', { name: 'Повторно' }).click();
  await page.getByText('145.png').click();
  await page.getByRole('button', { name: /Создать ИИ-кандидаты|Создать ИИ‑кандидаты/ }).click();
  await page.getByRole('tab', { name: /Проверить/ }).click();
  await expect(page.locator('.review-image')).toHaveAttribute('src', 'https://example.test/145.png');
  await expect(page.getByText('Исходный текст', { exact: true })).toBeVisible();
  await expect(page.getByText('안녕 f1...', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Открыть изображение крупно' }).click();
  await expect(page.locator('#imageDialog')).toBeVisible();
  await page.getByRole('button', { name: 'Закрыть изображение' }).click();
  await page.getByRole('button', { name: 'Принять' }).click();
  await expect.poll(() => accepted).toBe(true);
  await expect(page.locator('#message')).toContainText('Кандидат опубликован');
});
