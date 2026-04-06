// Скрипт для n8n Custom Code Tool (v2.12+)
// Улучшенная обработка объектов для контроля пояснений в скобках

const rawInput = (typeof query === 'object') ? query.input : query;
const inputStr = rawInput || "";

const parts = inputStr.split('|');
if (parts.length < 2) {
    return "ОШИБКА ФОРМАТА: Используй 'Термин1, Термин2 | Весь текст'. Ты передал: " + inputStr;
}

const terms = parts[0].split(',').map(t => t.trim());
const text = parts[1];
let missing = [];

terms.forEach(term => {
    if (!term) return;
    const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`${escapedTerm}\\s*\\([^)]+\\)`, 'i');
    if (!pattern.test(text)) {
        missing.push(term);
    }
});

if (missing.length === 0) {
    return "ВЕРДИКТ: OK. Все пояснения найдены.";
} else {
    return "ВЕРДИКТ: ОШИБКА! Добавь пояснения в скобках для: " + missing.join(', ') + ". Исправь текст и проверь снова.";
}
