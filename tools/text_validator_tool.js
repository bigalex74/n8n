// Скрипт для n8n Custom Code Tool (v2.12+)
// Улучшенная обработка объектов и строк для предотвращения имитации вызова

const rawInput = (typeof query === 'object') ? query.input : query;
const text = rawInput || "";
let issues = [];

// 1. Проверка на корейские иероглифы
const koreanRegex = /[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\ud7b0-\ud7ff]/g;
const koreanMatches = text.match(koreanRegex);
if (koreanMatches) {
    issues.push(`Корейские символы: ${koreanMatches.length} шт.`);
}

// 2. Проверка на английские буквы
const englishRegex = /[a-zA-Z]/g;
const englishMatches = text.match(englishRegex);
if (englishMatches) {
    issues.push(`Английские буквы: ${englishMatches.length} шт.`);
}

// 3. Проверка на тире в середине предложений
const lines = text.split('\n');
lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (trimmed.length > 1 && trimmed.slice(1).match(/[—–-]/)) {
        issues.push(`Линия ${index + 1}: запрещенное тире.`);
    }
});

if (issues.length === 0) {
    return "ВЕРДИКТ: OK. Техническая проверка пройдена.";
} else {
    return "ВЕРДИКТ: ОШИБКА! " + issues.join(" | ") + ". Исправь текст и вызови проверку снова.";
}
