const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

const PORTAL_DIR = '/home/user/n8n-docker/portal';
const DATA_FILE = path.join(PORTAL_DIR, 'data.json');
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'AdminPortal2025!';
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'bigalex';

// ============ DATA ============

const defaultData = {
  services: [
    { id: 'n8n', name: 'n8n', domain: 'bigalexn8n.ru', url: 'https://bigalexn8n.ru', port: 5678, auth: 'none', icon: '🤖', category: 'main', desc: 'Главная платформа автоматизации. Telegram-бот, AI workflows, интеграции' },
    { id: 'openwebui', name: 'Open WebUI', domain: 'ai.bigalexn8n.ru', url: 'https://ai.bigalexn8n.ru', port: 8080, auth: 'none', icon: '🧠', category: 'main', desc: 'Веб-интерфейс для локальных AI-моделей через Ollama' },
    { id: 'ollama', name: 'Ollama API', domain: 'ollama.bigalexn8n.ru', url: 'https://ollama.bigalexn8n.ru', port: 11434, auth: 'basic', icon: '⚙️', category: 'main', desc: 'Локальный AI API-сервер для запуска LLM-моделей' },
    { id: 'appshub', name: 'Apps Hub', domain: 'apps.bigalexn8n.ru', url: 'https://apps.bigalexn8n.ru', port: 8000, auth: 'none', icon: '📥', category: 'main', desc: 'Хаб приложений — FastAPI микросервисы + Telegram интеграции' },
    { id: 'grafana', name: 'Grafana', domain: 'grafana.bigalexn8n.ru', url: 'https://grafana.bigalexn8n.ru', port: 3000, auth: 'none', icon: '📈', category: 'monitoring', desc: 'Дашборды мониторинга, алерты, визуализация метрик' },
    { id: 'prometheus', name: 'Prometheus', domain: 'prometheus.bigalexn8n.ru', url: 'https://prometheus.bigalexn8n.ru', port: 9090, auth: 'none', icon: '🔥', category: 'monitoring', desc: 'Сбор и хранение метрик — system, Postgres, n8n' },
    { id: 'portainer', name: 'Portainer', domain: 'docker.bigalexn8n.ru', url: 'https://docker.bigalexn8n.ru', port: 9000, auth: 'none', icon: '🐳', category: 'devops', desc: 'Управление Docker-контейнерами через UI' },
    { id: 'crontab', name: 'Crontab UI', domain: 'cron.bigalexn8n.ru', url: 'https://cron.bigalexn8n.ru', port: 8001, auth: 'basic', icon: '⏰', category: 'devops', desc: 'Управление cron-задачами — автобэкапы каждые 4ч' },
    { id: 'drawio', name: 'Draw.io', domain: 'draw.bigalexn8n.ru', url: 'https://draw.bigalexn8n.ru', port: 24700, auth: 'none', icon: '📌', category: 'devops', desc: 'Редактор диаграмм и схем' },
    { id: 'pgadmin', name: 'pgAdmin 4', domain: 'pgadmin.bigalexn8n.ru', url: 'https://pgadmin.bigalexn8n.ru', port: 5055, auth: 'none', icon: '🐘', category: 'data', desc: 'Управление PostgreSQL — база данных n8n' },
    { id: 'lightrag', name: 'LightRAG', domain: 'lightrag.bigalexn8n.ru', url: 'https://lightrag.bigalexn8n.ru', port: 9621, auth: 'none', icon: '📚', category: 'data', desc: 'RAG-система — AI knowledge base с retrieval' },
    { id: 'searxng', name: 'SearXNG', domain: 'search.bigalexn8n.ru', url: 'https://search.bigalexn8n.ru', port: 8888, auth: 'basic', icon: '🔍', category: 'tools', desc: 'Приватный метапоисковик' },
    { id: 'firecrawl', name: 'Firecrawl', domain: 'firecrawl.bigalexn8n.ru', url: 'https://firecrawl.bigalexn8n.ru', port: 3002, auth: 'basic', icon: '🕸️', category: 'tools', desc: 'Web scraping и crawling API для AI' }
  ],
  roadmap: [
    { id: 'r1', title: 'Qwen Code MCP интеграция', desc: 'n8n-mcp + grafana-mcp для AI-управления', status: 'active', order: 1 },
    { id: 'r2', title: 'Telegram бот v2', desc: 'FSM состояния, Mini App, улучшенная архитектура', status: 'planned', order: 2 },
    { id: 'r3', title: 'Перевод книг', desc: 'PDF → OCR → перевод → публикация', status: 'planned', order: 3 },
    { id: 'r4', title: 'RAG knowledge base', desc: 'LightRAG для всей документации', status: 'planned', order: 4 },
    { id: 'r5', title: 'CI/CD pipeline', desc: 'Автодеплой из Git при пуше', status: 'planned', order: 5 },
    { id: 'r6', title: 'Home Dashboard', desc: 'Единый дашборд мониторинга', status: 'planned', order: 6 },
    { id: 'r7', title: 'Firecrawl production', desc: 'Веб-скрапинг для n8n workflows', status: 'planned', order: 7 },
    { id: 'r8', title: 'Security hardening', desc: 'Rate limiting, fail2ban, audit logs', status: 'planned', order: 8 }
  ],
  notes: ''
};

function loadData() {
  try {
    if (fs.existsSync(DATA_FILE)) {
      return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    }
  } catch (e) { console.error('Load error:', e.message); }
  return JSON.parse(JSON.stringify(defaultData));
}

function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
}

// Initialize data file
if (!fs.existsSync(DATA_FILE)) saveData(defaultData);

// ============ AUTH ============

function parseAuth(header) {
  if (!header || !header.startsWith('Basic ')) return null;
  const decoded = Buffer.from(header.slice(6), 'base64').toString('utf8');
  const [username, password] = decoded.split(':');
  return { username, password };
}

function checkAuth(req, res) {
  const auth = parseAuth(req.headers.authorization);
  if (!auth || auth.username !== ADMIN_USERNAME || auth.password !== ADMIN_PASSWORD) {
    res.writeHead(401, { 'WWW-Authenticate': 'Basic realm="Admin Panel"', 'Content-Type': 'text/plain' });
    res.end('Unauthorized');
    return false;
  }
  return true;
}

// ============ ROUTING ============

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.ico': 'image/x-icon'
};

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }

  // ---- API routes ----

  // GET /api/data or /data (after strip_prefix)
  if ((pathname === '/api/data' || pathname === '/data') && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(loadData()));
  }

  // POST /api/data or /data — update full data
  if ((pathname === '/api/data' || pathname === '/data') && req.method === 'POST') {
    if (!checkAuth(req, res)) return;
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const data = JSON.parse(body);
        saveData(data);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // GET /api/services
  if (pathname === '/api/services' && req.method === 'GET') {
    const data = loadData();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(data.services));
  }

  // PUT /api/services/:id
  if (pathname.match(/^\/api\/services\/[\w-]+$/) && req.method === 'PUT') {
    if (!checkAuth(req, res)) return;
    const id = pathname.split('/').pop();
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const data = loadData();
        const idx = data.services.findIndex(s => s.id === id);
        if (idx === -1) {
          res.writeHead(404, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ error: 'Not found' }));
        }
        data.services[idx] = { ...data.services[idx], ...JSON.parse(body) };
        saveData(data);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data.services[idx]));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // DELETE /api/services/:id
  if (pathname.match(/^\/api\/services\/[\w-]+$/) && req.method === 'DELETE') {
    if (!checkAuth(req, res)) return;
    const id = pathname.split('/').pop();
    const data = loadData();
    data.services = data.services.filter(s => s.id !== id);
    saveData(data);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ ok: true }));
  }

  // POST /api/services — add new service
  if (pathname === '/api/services' && req.method === 'POST') {
    if (!checkAuth(req, res)) return;
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const data = loadData();
        const service = JSON.parse(body);
        service.id = service.id || `svc-${Date.now()}`;
        data.services.push(service);
        saveData(data);
        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(service));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // POST /api/cli — run command via CLI
  if (pathname === '/api/cli' && req.method === 'POST') {
    if (!checkAuth(req, res)) return;
    let body = '';
    req.on('data', c => body += c);
    req.on('end', async () => {
      try {
        const { command, tool } = JSON.parse(body);
        if (!command) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ error: 'Command is required' }));
        }

        let fullCommand;
        if (tool === 'qwen') {
          fullCommand = `cd /home/user && qwen --output-format text --approval-mode yolo "${command.replace(/"/g, '\\"')}"`;
        } else if (tool === 'gemini') {
          fullCommand = `cd /home/user && gemini -p "${command.replace(/"/g, '\\"')}"`;
        } else if (tool === 'shell') {
          fullCommand = command;
        } else {
          fullCommand = `cd /home/user && qwen --output-format text "${command.replace(/"/g, '\\"')}"`;
        }

        // Set timeout to 5 minutes
        const { stdout, stderr } = await execAsync(fullCommand, {
          timeout: 300000,
          maxBuffer: 10 * 1024 * 1024, // 10MB
          env: { ...process.env, PATH: process.env.PATH + ':/home/user/.nvm/versions/node/v24.14.0/bin:/home/user/.local/bin' }
        });

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, stdout: stdout || '', stderr: stderr || '' }));
      } catch (e) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, stdout: e.stdout || '', stderr: e.stderr || '', error: e.message, code: e.code }));
      }
    });
    return;
  }

  // GET /api/health — check all services
  if (pathname === '/api/health' && req.method === 'GET') {
    const data = loadData();
    const results = await Promise.all(data.services.map(async (svc) => {
      try {
        const { stdout } = await execAsync(`curl -sk -o /dev/null -w "%{http_code}" --max-time 5 ${svc.url} 2>/dev/null`, { timeout: 10000 });
        const code = parseInt(stdout.trim());
        return { id: svc.id, domain: svc.domain, status: code >= 200 && code < 400 ? 'online' : 'offline', httpCode: code };
      } catch {
        return { id: svc.id, domain: svc.domain, status: 'offline', httpCode: 0 };
      }
    }));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(results));
  }

  // ---- Static files ----

  // Admin panel requires auth
  if (pathname.startsWith('/admin')) {
    if (!checkAuth(req, res)) return;
  }

  // Serve files
  let filePath;
  if (pathname === '/admin') {
    filePath = path.join(PORTAL_DIR, 'admin.html');
  } else if (pathname === '/' || pathname === '/index.html') {
    filePath = path.join(PORTAL_DIR, 'index.html');
  } else {
    filePath = path.join(PORTAL_DIR, pathname);
  }

  const ext = path.extname(filePath);
  const mimeType = MIME_TYPES[ext] || 'application/octet-stream';

  try {
    const content = fs.readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': mimeType });
    res.end(content);
  } catch (e) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not Found');
  }
});

server.listen(3080, '127.0.0.1', () => {
  console.log(`Portal API server running on http://127.0.0.1:3080`);
  console.log(`Admin panel: http://127.0.0.1:3080/admin`);
});
