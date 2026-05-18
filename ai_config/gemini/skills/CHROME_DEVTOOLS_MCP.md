# Chrome DevTools MCP — Правила и сценарии использования

## Что это и зачем

Chrome DevTools MCP предоставляет прямой доступ к браузеру через инструменты:
навигация, клики, ввод текста, скриншоты, DOM-снапшоты, консоль, сеть, Performance.

**Главное отличие от browser_subagent:**
| | Chrome DevTools MCP | browser_subagent |
|---|---|---|
| Управление | Прямые tool-calls в той же сессии | Отдельный агент-подпроцесс |
| Скорость | Быстро (нет overhead агента) | Медленнее |
| Контроль | Полный, пошаговый | Только описание задачи |
| Когда | Точечные проверки, инспекция | Сложные сценарии с UI-логикой |

---

## Доступные инструменты

### Навигация и страницы
- `list_pages` — список открытых вкладок (всегда начинай с этого)
- `select_page(pageId)` — переключиться на вкладку
- `navigate_page(type, url)` — перейти по URL / back / forward / reload
- `new_page(url)` — открыть новую вкладку
- `close_page(pageId)` — закрыть вкладку

### Взаимодействие
- `take_snapshot()` — **главный инструмент**: a11y-дерево с uid для всех элементов
- `click(uid)` — клик по элементу (uid из snapshot)
- `fill(uid, value)` — ввод текста в поле
- `fill_form(elements)` — заполнить несколько полей сразу
- `hover(uid)` — наведение мыши
- `press_key(key)` — нажать клавишу (Enter, Escape, Tab, Control+A...)
- `drag(from_uid, to_uid)` — drag-and-drop
- `upload_file(uid, filePath)` — загрузка файла

### Снимки и анализ
- `take_screenshot()` — скриншот страницы или элемента (uid)
- `evaluate_script(function)` — выполнить JavaScript в браузере
- `list_console_messages()` — список сообщений консоли
- `get_console_message(msgid)` — детали сообщения консоли
- `list_network_requests()` — список сетевых запросов
- `get_network_request(reqid)` — детали запроса (заголовки, тело, ответ)

### Эмуляция
- `emulate(viewport, colorScheme, networkConditions, geolocation)` — эмуляция устройства/условий
- `resize_page(width, height)` — изменить размер окна

### Производительность
- `performance_start_trace()` — начать трассировку
- `performance_stop_trace()` — остановить, получить метрики
- `performance_analyze_insight(insightSetId, insightName)` — анализ конкретного insight
- `lighthouse_audit()` — аудит accessibility, SEO, best practices

### Диалоги
- `handle_dialog(action)` — принять/отклонить alert/confirm/prompt
- `wait_for(text)` — ждать появления текста на странице

---

## Рабочий процесс (обязательный порядок)

```
1. list_pages           — узнать что открыто
2. navigate_page(url)   — перейти на нужную страницу
3. wait_for(text)       — убедиться что страница загрузилась
4. take_snapshot()      — получить DOM с uid-ами элементов
5. click/fill/...       — взаимодействие по uid
6. take_screenshot()    — зафиксировать результат
```

> **ВАЖНО:** Всегда бери `take_snapshot()` перед кликами — uid меняются при ре-рендере.
> Никогда не используй uid из предыдущего snapshot после изменений DOM.

---

## Сценарии использования

### UI-проверка после деплоя (вместо browser_subagent)
```
Задача: Убедиться что модалка отображается корректно

1. navigate_page(url='http://localhost:8002')
2. wait_for(['Мои переводы'])
3. take_screenshot()           — главный экран
4. take_snapshot()             — найти uid кнопки ▶
5. click(uid=...)              — нажать «Запустить заново»
6. take_screenshot()           — скриншот модалки
7. evaluate_script(() => {
     const el = document.querySelector('.modal-overlay');
     return getComputedStyle(el).background;
   })                          — программно проверить фон overlay
```

### Отладка сетевых запросов
```
1. navigate_page(url)
2. list_network_requests(resourceTypes=['fetch','xhr'])
3. get_network_request(reqid)  — посмотреть заголовки и тело ответа
```

### Проверка Service Worker / кэша
```
1. navigate_page(url)
2. list_console_messages()     — искать [SW] логи
3. list_network_requests()     — смотреть Cache-Control заголовки
```

### Эмуляция мобильного устройства
```
1. emulate(viewport='375x812x2,mobile,touch')
2. navigate_page(url)
3. take_screenshot()
```

### Performance аудит
```
1. navigate_page(url)          — перейти на нужную страницу
2. performance_start_trace()   — начать трассировку (автоматически перезагружает)
3. performance_stop_trace()    — получить метрики
4. performance_analyze_insight(insightSetId, 'LCPBreakdown')
```

---

## Правила и ограничения

### Когда ИСПОЛЬЗОВАТЬ Chrome DevTools MCP:
- ✅ Визуальная проверка UI после CSS-изменений
- ✅ Проверка что модалки/тосты отображаются правильно
- ✅ Отладка сетевых запросов (SW, кэш, заголовки)
- ✅ Проверка console errors после деплоя
- ✅ Lighthouse audit перед релизом
- ✅ Эмуляция мобильных устройств
- ✅ Performance трассировка

### Когда НЕ использовать (предпочесть другое):
- ❌ Долгие сложные сценарии с условной логикой → `browser_subagent`
- ❌ E2E тесты с assertions → `Playwright (make test:e2e)`
- ❌ Простая проверка URL → `curl`

### Антипаттерны:
- ❌ Не используй uid без предварительного `take_snapshot()`
- ❌ Не делай клик без `wait_for()` — страница может не загрузиться
- ❌ Не забывай закрывать лишние вкладки через `close_page()`
- ❌ Не запускай `performance_start_trace` без предварительного navigate

---

## Для проекта translateVideo

**Стандартные URL:**
- Prod: `https://video.bigalexn8n.ru`
- Local: `http://localhost:8002`
- Dev: `http://localhost:5174`

**Стандартная проверка после деплоя:**
```
1. navigate_page('http://localhost:8002')
2. wait_for(['Мои переводы', 'My translations'])
3. take_screenshot()
4. list_console_messages(types=['error','warn'])  — нет ли ошибок?
5. list_network_requests()                        — sw.js с no-store?
```
