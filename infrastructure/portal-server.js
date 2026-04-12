const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { exec } = require('child_process');
const { promisify } = require('util');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const execAsync = promisify(exec);

const PORTAL_DIR = '/home/user/n8n-docker/portal';
const DATA_FILE = path.join(PORTAL_DIR, 'data.json');
const JWT_SECRET_FILE = path.join(PORTAL_DIR, 'jwt-secret.json');
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'bigalex';
const DEFAULT_PASSWORD = 'AdminPortal2025!';
const JWT_EXPIRES_IN = '30d';
const BCRYPT_ROUNDS = 10;

// Rate limiter for login
const loginAttempts = new Map();
const LOGIN_MAX_ATTEMPTS = 5;
const LOGIN_WINDOW_MS = 60 * 1000; // 60 seconds

// ============ JWT SECRET MANAGEMENT ============

function initJwtSecret() {
  try {
    if (fs.existsSync(JWT_SECRET_FILE)) {
      const raw = fs.readFileSync(JWT_SECRET_FILE, 'utf8');
      const parsed = JSON.parse(raw);
      return parsed;
    }
  } catch (e) {
    console.error('Error loading JWT secret:', e.message);
  }

  // Generate new secret and hash default password
  const secret = crypto.randomBytes(32).toString('hex');
  const passwordHash = bcrypt.hashSync(DEFAULT_PASSWORD, BCRYPT_ROUNDS);

  const data = { secret, passwordHash };
  fs.writeFileSync(JWT_SECRET_FILE, JSON.stringify(data, null, 2), 'utf8');
  console.log('Generated new JWT secret and hashed default password');
  return data;
}

let jwtConfig = initJwtSecret();

function loadJwtConfig() {
  try {
    if (fs.existsSync(JWT_SECRET_FILE)) {
      jwtConfig = JSON.parse(fs.readFileSync(JWT_SECRET_FILE, 'utf8'));
    }
  } catch (e) {
    console.error('Error reloading JWT config:', e.message);
  }
}

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

// ============ JWT MIDDLEWARE ============

function getBearerToken(req) {
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) return null;
  return auth.slice(7);
}

function authenticateJWT(req, res) {
  const token = getBearerToken(req);
  if (!token) {
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'No token provided' }));
    return null;
  }

  try {
    const decoded = jwt.verify(token, jwtConfig.secret);
    return decoded;
  } catch (e) {
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid or expired token' }));
    return null;
  }
}

// ============ RATE LIMITER ============

function checkRateLimit(req, res) {
  const ip = req.socket.remoteAddress || 'unknown';
  const now = Date.now();
  const attempt = loginAttempts.get(ip);

  if (attempt) {
    if (now > attempt.resetTime) {
      // Window expired, reset
      loginAttempts.set(ip, { count: 1, resetTime: now + LOGIN_WINDOW_MS });
      return true;
    }
    if (attempt.count >= LOGIN_MAX_ATTEMPTS) {
      res.writeHead(429, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Too many login attempts. Try again later.' }));
      return false;
    }
    attempt.count++;
  } else {
    loginAttempts.set(ip, { count: 1, resetTime: now + LOGIN_WINDOW_MS });
  }
  return true;
}

// Clean up old rate limit entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [ip, attempt] of loginAttempts.entries()) {
    if (now > attempt.resetTime) {
      loginAttempts.delete(ip);
    }
  }
}, 5 * 60 * 1000); // every 5 minutes

// ============ BODY PARSER ============

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on('error', reject);
  });
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

  // POST /api/login
  if (pathname === '/api/login' && req.method === 'POST') {
    if (!checkRateLimit(req, res)) return;

    let body;
    try {
      body = await parseBody(req);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }

    const { username, password } = body;

    if (username !== ADMIN_USERNAME) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid credentials' }));
    }

    const valid = bcrypt.compareSync(password, jwtConfig.passwordHash);
    if (!valid) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid credentials' }));
    }

    const token = jwt.sign({ username }, jwtConfig.secret, { expiresIn: JWT_EXPIRES_IN });
    const decoded = jwt.decode(token);

    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({
      token,
      user: { username },
      expiresIn: JWT_EXPIRES_IN
    }));
  }

  // POST /api/change-password
  if (pathname === '/api/change-password' && req.method === 'POST') {
    const decoded = authenticateJWT(req, res);
    if (!decoded) return;

    let body;
    try {
      body = await parseBody(req);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }

    const { currentPassword, newPassword } = body;

    if (!currentPassword || !newPassword) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'currentPassword and newPassword are required' }));
    }

    // Verify current password
    const valid = bcrypt.compareSync(currentPassword, jwtConfig.passwordHash);
    if (!valid) {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Current password is incorrect' }));
    }

    // Hash new password and regenerate secret (logout all sessions)
    const newSecret = crypto.randomBytes(32).toString('hex');
    const newHash = bcrypt.hashSync(newPassword, BCRYPT_ROUNDS);

    jwtConfig = { secret: newSecret, passwordHash: newHash };
    fs.writeFileSync(JWT_SECRET_FILE, JSON.stringify(jwtConfig, null, 2), 'utf8');

    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ ok: true }));
  }

  // GET /api/me
  if (pathname === '/api/me' && req.method === 'GET') {
    const decoded = authenticateJWT(req, res);
    if (!decoded) return;

    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({
      username: decoded.username,
      iat: decoded.iat,
      exp: decoded.exp
    }));
  }

  // GET /api/data
  if ((pathname === '/api/data' || pathname === '/data') && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(loadData()));
  }

  // POST /api/data — update full data (JWT required)
  if ((pathname === '/api/data' || pathname === '/data') && req.method === 'POST') {
    const decoded = authenticateJWT(req, res);
    if (!decoded) return;

    let body;
    try {
      body = await parseBody(req);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }

    try {
      saveData(body);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true }));
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // GET /api/services
  if (pathname === '/api/services' && req.method === 'GET') {
    const data = loadData();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(data.services));
  }

  // PUT /api/services/:id (JWT required)
  if (pathname.match(/^\/api\/services\/[\w-]+$/) && req.method === 'PUT') {
    const decoded = authenticateJWT(req, res);
    if (!decoded) return;

    const id = pathname.split('/').pop();
    let body;
    try {
      body = await parseBody(req);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }

    try {
      const data = loadData();
      const idx = data.services.findIndex(s => s.id === id);
      if (idx === -1) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: 'Not found' }));
      }
      data.services[idx] = { ...data.services[idx], ...body };
      saveData(data);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data.services[idx]));
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // DELETE /api/services/:id (JWT required)
  if (pathname.match(/^\/api\/services\/[\w-]+$/) && req.method === 'DELETE') {
    const decoded = authenticateJWT(req, res);
    if (!decoded) return;

    const id = pathname.split('/').pop();
    const data = loadData();
    data.services = data.services.filter(s => s.id !== id);
    saveData(data);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ ok: true }));
  }

  // POST /api/services — add new service (JWT required)
  if (pathname === '/api/services' && req.method === 'POST') {
    const decoded = authenticateJWT(req, res);
    if (!decoded) return;

    let body;
    try {
      body = await parseBody(req);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }

    try {
      const data = loadData();
      const service = body;
      service.id = service.id || `svc-${Date.now()}`;
      data.services.push(service);
      saveData(data);
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(service));
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // POST /api/cli — run command via CLI (JWT required)
  if (pathname === '/api/cli' && req.method === 'POST') {
    const decoded = authenticateJWT(req, res);
    if (!decoded) return;

    let body;
    try {
      body = await parseBody(req);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Invalid JSON' }));
    }

    try {
      const { command, tool } = body;
      if (!command) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: 'Command is required' }));
      }

      let fullCommand;
      if (tool === 'qwen') {
        fullCommand = `cd /home/user && qwen --output-format text --approval-mode yolo "${command.replace(/"/g, '\\"')}"`;
      } else if (tool === 'gemini') {
        fullCommand = `echo "${command.replace(/"/g, '\\"')}" | gemini`;
      } else if (tool === 'shell') {
        fullCommand = command;
      } else {
        fullCommand = `cd /home/user && qwen --output-format text "${command.replace(/"/g, '\\"')}"`;
      }

      const { stdout, stderr } = await execAsync(fullCommand, {
        timeout: 300000,
        maxBuffer: 10 * 1024 * 1024,
        env: { ...process.env, PATH: process.env.PATH + ':/home/user/.nvm/versions/node/v24.14.0/bin:/home/user/.local/bin' }
      });

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, stdout: stdout || '', stderr: stderr || '' }));
    } catch (e) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, stdout: e.stdout || '', stderr: e.stderr || '', error: e.message, code: e.code }));
    }
    return;
  }

  // GET /api/health — check all services (public)
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

  // ============ CATEGORY CRUD ============

  // GET /api/categories (public)
  if ((pathname === '/api/categories' || pathname === '/api/categories/') && req.method === 'GET') {
    const data = loadData();
    const cats = (data.categories || []).sort((a, b) => (a.order || 0) - (b.order || 0));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify(cats));
  }

  // POST /api/categories — create category (JWT required)
  if (pathname === '/api/categories' && req.method === 'POST') {
    if (!authenticateJWT(req, res)) return;
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const data = loadData();
        if (!data.categories) data.categories = [];
        const cat = JSON.parse(body);
        cat.id = cat.id || `cat-${Date.now()}`;
        cat.order = data.categories.length + 1;
        data.categories.push(cat);
        saveData(data);
        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(cat));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // PUT /api/categories/:id — update category (JWT required)
  if (pathname.match(/^\/api\/categories\/[\w-]+$/) && req.method === 'PUT') {
    if (!authenticateJWT(req, res)) return;
    const id = pathname.split('/').pop();
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const data = loadData();
        const idx = (data.categories || []).findIndex(c => c.id === id);
        if (idx === -1) {
          res.writeHead(404, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ error: 'Category not found' }));
        }
        // Check for duplicate name
        const newName = JSON.parse(body).name;
        if (newName && data.categories.some((c, i) => i !== idx && c.name === newName)) {
          res.writeHead(409, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ error: 'Category with this name already exists' }));
        }
        data.categories[idx] = { ...data.categories[idx], ...JSON.parse(body) };
        saveData(data);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data.categories[idx]));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  // DELETE /api/categories/:id — delete category (JWT required)
  if (pathname.match(/^\/api\/categories\/[\w-]+$/) && req.method === 'DELETE') {
    if (!authenticateJWT(req, res)) return;
    const id = pathname.split('/').pop();
    const data = loadData();
    const catIdx = (data.categories || []).findIndex(c => c.id === id);
    if (catIdx === -1) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: 'Category not found' }));
    }
    // Move services to first available category or 'uncategorized'
    const fallbackCat = data.categories.find(c => c.id !== id)?.id || 'uncategorized';
    data.services.forEach(svc => {
      if (svc.category === id) svc.category = fallbackCat;
    });
    data.categories.splice(catIdx, 1);
    saveData(data);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ ok: true, fallbackCategory: fallbackCat }));
  }

  // ---- Static files ----

  // Serve files
  let filePath;
  if (pathname === '/admin' || pathname.startsWith('/admin')) {
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
  console.log(`JWT auth enabled`);
});
