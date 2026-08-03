# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e_ocr.spec.js >> OCR screen shows authenticated production status and safe launch flow
- Location: e2e_ocr.spec.js:3:1

# Error details

```
Error: OCR_E2E_INIT_DATA is required
```

# Test source

```ts
  1   | const { test, expect } = require('@playwright/test');
  2   | 
  3   | test('OCR screen shows authenticated production status and safe launch flow', async ({ page }) => {
  4   |   const initData = process.env.OCR_E2E_INIT_DATA;
> 5   |   if (!initData) throw new Error('OCR_E2E_INIT_DATA is required');
      |                        ^ Error: OCR_E2E_INIT_DATA is required
  6   | 
  7   |   await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
  8   |     await route.fulfill({
  9   |       contentType: 'application/javascript',
  10  |       body: `window.Telegram = { WebApp: {
  11  |         initData: ${JSON.stringify(initData)},
  12  |         ready() {}, expand() {},
  13  |         BackButton: { show() {}, onClick() {} },
  14  |         HapticFeedback: { notificationOccurred() {} },
  15  |         showConfirm(_text, callback) { callback(true); }
  16  |       }};`,
  17  |     });
  18  |   });
  19  | 
  20  |   let startCalled = false;
  21  |   await page.route('**/api/ocr/start', async route => {
  22  |     startCalled = true;
  23  |     await route.fulfill({
  24  |       status: 202,
  25  |       contentType: 'application/json',
  26  |       body: JSON.stringify({ accepted: true, message: 'OCR batch accepted' }),
  27  |     });
  28  |   });
  29  | 
  30  |   await page.goto('/ocr');
  31  |   await expect(page.getByRole('heading', { name: 'OCR изображений' })).toBeVisible();
  32  |   await expect(page.locator('#serviceStatus')).toContainText(/готов/i);
  33  |   await expect(page.locator('#sourceFolder')).toHaveText('протокол');
  34  |   await expect(page.getByRole('button', { name: 'Запустить OCR' })).toBeEnabled();
  35  | 
  36  |   await page.getByRole('button', { name: 'Запустить OCR' }).click();
  37  |   await expect.poll(() => startCalled).toBe(true);
  38  |   await expect(page.locator('#message')).toContainText('Запуск принят');
  39  | });
  40  | 
  41  | test('OCR screen blocks a browser opened outside Telegram', async ({ page }) => {
  42  |   await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
  43  |     await route.fulfill({
  44  |       contentType: 'application/javascript',
  45  |       body: 'window.Telegram = { WebApp: { initData: "", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} } } };',
  46  |     });
  47  |   });
  48  |   await page.goto('/ocr');
  49  |   await expect(page.getByRole('button', { name: 'Запустить OCR' })).toBeDisabled();
  50  |   await expect(page.locator('#message')).toContainText('Откройте приложение через Telegram');
  51  | });
  52  | 
  53  | test('OCR screen renders live progress without Telegram message fan-out', async ({ page }) => {
  54  |   await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
  55  |     await route.fulfill({
  56  |       contentType: 'application/javascript',
  57  |       body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, showConfirm(_text, callback) { callback(true); } } };',
  58  |     });
  59  |   });
  60  |   await page.route('**/api/ocr/status', async route => {
  61  |     await route.fulfill({
  62  |       status: 200,
  63  |       contentType: 'application/json',
  64  |       body: JSON.stringify({
  65  |           source_folder: 'протокол',
  66  |           service: { ready: true },
  67  |           can_start: false,
  68  |           can_stop: true,
  69  |         batch: {
  70  |           status: 'running', started_at: '2026-07-16T10:00:00Z',
  71  |           progress_total: 121, progress_completed: 60,
  72  |           progress_failed: 1, progress_current_file: '161.png',
  73  |         },
  74  |       }),
  75  |     });
  76  |   });
  77  |   let stopCalled = false;
  78  |   await page.route('**/api/ocr/stop', async route => {
  79  |     stopCalled = true;
  80  |     await route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ accepted: true }) });
  81  |   });
  82  | 
  83  |   await page.goto('/ocr');
  84  |   await expect(page.locator('#progressPanel')).toBeVisible();
  85  |   await expect(page.locator('#progressPercent')).toHaveText('50%');
  86  |   await expect(page.locator('#progressDetail')).toContainText('61 из 121');
  87  |   await expect(page.locator('#progressDetail')).toContainText('161.png');
  88  |   await expect(page.getByRole('button', { name: 'Запустить OCR' })).toBeDisabled();
  89  |   await expect(page.getByRole('button', { name: 'Остановить OCR' })).toBeVisible();
  90  |   await page.getByRole('button', { name: 'Остановить OCR' }).click();
  91  |   await expect.poll(() => stopCalled).toBe(true);
  92  |   await expect(page.locator('#message')).toContainText('Останавливаю');
  93  | });
  94  | 
  95  | test('OCR screen reprocesses selected images only', async ({ page }) => {
  96  |   await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
  97  |     await route.fulfill({
  98  |       contentType: 'application/javascript',
  99  |       body: 'window.Telegram = { WebApp: { initData: "signed-test-data", ready() {}, expand() {}, BackButton: { show() {}, onClick() {} }, showConfirm(_text, callback) { callback(true); } } };',
  100 |     });
  101 |   });
  102 |   await page.route('**/api/ocr/status', async route => route.fulfill({
  103 |     status: 200, contentType: 'application/json',
  104 |     body: JSON.stringify({ source_folder: 'протокол', service: { ready: true }, can_start: true, can_stop: false, batch: { status: 'done' } }),
  105 |   }));
```