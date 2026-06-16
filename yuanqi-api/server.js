const http = require('http');
const data = require('./etf_data.json');

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (req.method === 'OPTIONS') {
    res.writeHead(200); res.end(); return;
  }

  if (req.url === '/api/compare' && (req.method === 'POST' || req.method === 'GET')) {
    if (req.method === 'GET') {
      const u = new URL(req.url, 'http://localhost');
      const code1 = u.searchParams.get('etf_code1') || '';
      const code2 = u.searchParams.get('etf_code2') || '';
      respond(code1, code2);
    } else {
      let body = '';
      req.on('data', c => body += c);
      req.on('end', () => {
        try {
          const { etf_code1, etf_code2 } = JSON.parse(body);
          respond(etf_code1 || '', etf_code2 || '');
        } catch (e) {
          res.writeHead(400);
          res.end(JSON.stringify({ error: '请求格式错误' }));
        }
      });
    }
    return;
  }

  if (req.url === '/api/health') {
    res.writeHead(200);
    res.end(JSON.stringify({ status: 'ok', etfs: Object.keys(data).length }));
    return;
  }

  if (req.url === '/api/search' && req.method === 'GET') {
    const u = new URL(req.url, 'http://localhost');
    const kw = (u.searchParams.get('keyword') || '').toLowerCase();
    const results = Object.values(data).filter(e =>
      e.name.includes(kw) || e.code.includes(kw)
    ).slice(0, 10).map(e => ({ code: e.code, name: e.name, issuer: e.issuer }));
    res.writeHead(200);
    res.end(JSON.stringify({ results }));
    return;
  }

  res.writeHead(404);
  res.end(JSON.stringify({ error: 'Not found' }));

  function respond(code1, code2) {
    if (!code1 || !code2) {
      res.writeHead(400);
      res.end(JSON.stringify({ error: '请提供 etf_code1 和 etf_code2' }));
      return;
    }
    const e1 = data[code1];
    const e2 = data[code2];
    if (!e1 || !e2) {
      res.writeHead(404);
      res.end(JSON.stringify({ error: `未找到: ${[code1, code2].filter(c => !data[c]).join(',')}` }));
      return;
    }
    res.writeHead(200);
    res.end(JSON.stringify({ etf1: e1, etf2: e2 }));
  }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => console.log(`ETF API → http://localhost:${PORT}`));
