#!/usr/bin/env python3
"""ETF MCP Server — HTTP/SSE transport，SQLite 直连"""
import json, sqlite3, sys
from http.server import HTTPServer, BaseHTTPRequestHandler

DB = '/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_data.db'
PORT = 8888

class ETFHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        
        method = body.get('method', '')
        params = body.get('params', {})
        rid = body.get('id', 0)
        
        db = sqlite3.connect(DB)
        db.row_factory = sqlite3.Row
        c = db.cursor()
        
        result = None
        error = None
        
        try:
            if method == 'tools/list':
                result = {"tools": [
                    {"name": "etf_query", "description": "SQL查询ETF数据库，1685只全市场ETF", "inputSchema": {
                        "type": "object", "properties": {"sql": {"type": "string", "description": "SQL语句"}}, "required": ["sql"]
                    }},
                    {"name": "etf_search", "description": "按名称/代码搜索ETF", "inputSchema": {
                        "type": "object", "properties": {"keyword": {"type": "string"}}, "required": ["keyword"]
                    }},
                    {"name": "etf_compare", "description": "对比多只ETF核心指标", "inputSchema": {
                        "type": "object", "properties": {"codes": {"type": "array", "items": {"type": "string"}}}, "required": ["codes"]
                    }},
                    {"name": "etf_rank", "description": "按字段排名ETF", "inputSchema": {
                        "type": "object", "properties": {"field": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["field"]
                    }},
                ]}
            
            elif method == 'tools/call':
                tool = params.get('name', '')
                args = params.get('arguments', {})
                
                if tool == 'etf_query':
                    c.execute(args['sql'])
                    rows = [dict(r) for r in c.fetchall()]
                    result = {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False, default=str)}]}
                
                elif tool == 'etf_search':
                    kw = args['keyword']
                    c.execute("SELECT code,name,issuer,category,scale_yi FROM etfs WHERE name LIKE ? OR code LIKE ? OR issuer LIKE ? LIMIT 10",
                              (f'%{kw}%', f'%{kw}%', f'%{kw}%'))
                    rows = [dict(r) for r in c.fetchall()]
                    result = {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False)}]}
                
                elif tool == 'etf_compare':
                    codes = args.get('codes', [])
                    placeholders = ','.join('?' * len(codes))
                    c.execute(f"SELECT * FROM etfs WHERE code IN ({placeholders})", codes)
                    rows = [dict(r) for r in c.fetchall()]
                    result = {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False, default=str)}]}
                
                elif tool == 'etf_rank':
                    field = args['field']
                    limit = args.get('limit', 10)
                    valid = {'scale_yi','year_1_return','sharpe_ratio','fee_total','max_drawdown','annual_vol'}
                    if field not in valid:
                        error = {"code": -1, "message": f"无效字段，可选: {valid}"}
                    else:
                        c.execute(f"SELECT code,name,issuer,{field} FROM etfs WHERE {field} IS NOT NULL AND {field} != 0 ORDER BY {field} DESC LIMIT ?", (limit,))
                        rows = [dict(r) for r in c.fetchall()]
                        result = {"content": [{"type": "text", "text": json.dumps(rows, ensure_ascii=False, default=str)}]}
            
            elif method == 'initialize':
                result = {"protocolVersion": "2024-11-05", "serverInfo": {"name": "ETF MCP", "version": "1.0"}, "capabilities": {"tools": {}}}
        
        except Exception as e:
            error = {"code": -1, "message": str(e)}
        
        db.close()
        
        resp = {"jsonrpc": "2.0", "id": rid}
        if result is not None: resp["result"] = result
        if error is not None: resp["error"] = error
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(resp, ensure_ascii=False, default=str).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), ETFHandler)
    print(f'ETF MCP Server → http://127.0.0.1:{PORT}')
    server.serve_forever()
