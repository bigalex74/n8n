# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e_translation.spec.js >> E2E: Translation process flow
- Location: e2e_translation.spec.js:3:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForSelector: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('#sel-file option:nth-child(2)') to be visible

```

# Test source

```ts
  1  | const { test, expect } = require('@playwright/test');
  2  | 
  3  | test('E2E: Translation process flow', async ({ page }) => {
  4  |   await page.goto('/files');
  5  |   
  6  |   // 1. Ждем инициализации
> 7  |   await page.waitForSelector('#sel-file option:nth-child(2)');
     |              ^ Error: page.waitForSelector: Test timeout of 30000ms exceeded.
  8  |   
  9  |   // 2. Заполнение формы
  10 |   await page.selectOption('#sel-file', { index: 1 }); // Выбор файла
  11 |   await page.selectOption('#glossary-mode', 'create_ai'); // AI Глоссарий
  12 |   await page.selectOption('#sel-bp', { index: 1 }); // Промпт
  13 |   await page.selectOption('#sel-pp', { index: 1 }); // Редактор
  14 |   
  15 |   // 3. Проверка активации кнопки
  16 |   const startBtn = page.locator('#btn-start');
  17 |   await expect(startBtn).toBeEnabled();
  18 |   
  19 |   // 4. Запуск (используем click)
  20 |   await startBtn.click();
  21 |   
  22 |   // В успешном сценарии страница должна закрыться или перенаправиться.
  23 |   // Playwright проверит навигацию или закрытие.
  24 | });
  25 | 
```