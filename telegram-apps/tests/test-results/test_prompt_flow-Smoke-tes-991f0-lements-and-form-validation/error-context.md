# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_prompt_flow.spec.js >> Smoke test: verify UI elements and form validation
- Location: test_prompt_flow.spec.js:3:1

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
  3  | test('Smoke test: verify UI elements and form validation', async ({ page }) => {
  4  |   await page.goto('/files');
  5  |   
> 6  |   await page.waitForSelector('#sel-file option:nth-child(2)');
     |              ^ Error: page.waitForSelector: Test timeout of 30000ms exceeded.
  7  |   
  8  |   const startBtn = page.locator('#btn-start');
  9  |   await expect(startBtn).toBeDisabled();
  10 | 
  11 |   // Выбор файла и глоссария
  12 |   await page.selectOption('#sel-file', { index: 1 });
  13 |   await page.selectOption('#glossary-mode', 'create_ai');
  14 |   
  15 |   // Кнопка должна стать активной
  16 |   await expect(startBtn).toBeEnabled();
  17 | });
  18 | 
```