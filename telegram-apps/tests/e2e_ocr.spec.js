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
  await expect(page.locator('#serviceStatus')).toContainText('Готов');
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
