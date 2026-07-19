const { test, expect } = require('@playwright/test');

async function mockTelegram(page) {
  await page.route('https://telegram.org/js/telegram-web-app.js', async route => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: `window.Telegram = { WebApp: {
        initData: "signed-test-data",
        expand() {},
        BackButton: { show() {}, onClick() {} },
        MainButton: { showProgress() {}, hideProgress() {} },
        showConfirm(_text, callback) { callback(true); }
      }};`,
    });
  });
}

test('TGS screen converts SVG and confirms destructive actions', async ({ page }) => {
  await mockTelegram(page);

  await page.route('**/api/tgs/status', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        folder_path: '/Yulia/+ Test/tgs',
        svg_count: 2,
        tgs_count: 1,
        files: [
          { name: 'row1-03.svg' },
          { name: 'row1-04.svg' },
          { name: 'row1-03.tgs' },
        ],
      }),
    });
  });

  let convertCalled = false;
  let deleteRequest = null;
  await page.route('**/api/tgs/convert', async route => {
    convertCalled = true;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ converted_count: 2 }),
    });
  });
  await page.route('**/api/tgs/delete', async route => {
    deleteRequest = await route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ deleted_count: 2 }),
    });
  });

  await page.goto('/tgs');
  await expect(page.getByRole('heading', { name: 'SVG → TGS' })).toBeVisible();
  await expect(page.locator('#svgCount')).toHaveText('2');
  await expect(page.locator('#tgsCount')).toHaveText('1');

  await page.getByRole('button', { name: 'Конвертировать в tgs' }).click();
  await expect.poll(() => convertCalled).toBe(true);
  await expect(page.locator('#message')).toContainText('Все файлы сконвертированы');

  await page.getByRole('button', { name: 'Удалить все файлы svg' }).click();
  await expect.poll(() => deleteRequest).toEqual({
    scope: 'svg',
    confirmation: 'DELETE_ALL_SVG',
  });
});
