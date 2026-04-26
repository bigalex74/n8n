import requests
from flask import Flask, request, Response
import json
import os
import sys

app = Flask(__name__)
PROXIES = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}
G_KEY = os.getenv("GOOGLE_AI_STUDIO_KEY")

def log(msg):
    print(msg, file=sys.stdout, flush=True)

@app.route('/models', methods=['GET'])
@app.route('/v1/models', methods=['GET'])
def list_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={G_KEY}"
    try:
        resp = requests.get(url, proxies=PROXIES, timeout=30)
        if resp.status_code == 200:
            google_data = resp.json()
            openai_models = []
            for m in google_data.get('models', []):
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    model_id = m['name'].replace('models/', '')
                    openai_models.append({"id": model_id, "object": "model", "owned_by": "google"})
            return Response(json.dumps({"object": "list", "data": openai_models}), 200, {'Content-Type':'application/json'})
        return Response(resp.content, resp.status_code, {'Content-Type':'application/json'})
    except Exception as e: return str(e), 500

@app.route('/chat/completions', methods=['POST'])
@app.route('/v1/chat/completions', methods=['POST'])
@app.route('/responses', methods=['POST'])
@app.route('/v1/responses', methods=['POST'])
def chat():
    url = f'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions?key={G_KEY}'
    
    headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'content-length', 'authorization', 'connection']}
    headers['Authorization'] = f'Bearer {G_KEY}'
    
    data = request.get_data()
    if request.is_json:
        try:
            payload = request.get_json()
            
            # --- ЖЕСТКАЯ ОЧИСТКА ДЛЯ GOOGLE ---
            clean_payload = {}
            
            # 1. Модель
            if 'model' in payload:
                clean_payload['model'] = payload['model'].split('/')[-1]
            else:
                clean_payload['model'] = 'gemini-2.0-flash'

            # 2. Сообщения (конвертируем из input если нужно)
            if 'input' in payload and isinstance(payload['input'], list):
                clean_payload['messages'] = [{"role": m.get('role', 'user'), "content": m.get('content', '')} for m in payload['input']]
            elif 'messages' in payload:
                clean_payload['messages'] = payload['messages']
            
            # 3. Базовые параметры
            for key in ['temperature', 'top_p', 'n', 'stream', 'stop', 'max_tokens', 'presence_penalty', 'frequency_penalty']:
                if key in payload:
                    clean_payload[key] = payload[key]

            # 4. Tools (только если не пустые)
            if 'tools' in payload and payload['tools']:
                clean_payload['tools'] = payload['tools']
                if 'tool_choice' in payload:
                    clean_payload['tool_choice'] = payload['tool_choice']

            # ПОЛЕ 'text' И ДРУГОЙ МУСОР ТЕПЕРЬ ТОЧНО НЕ ПОПАДУТ
            data = json.dumps(clean_payload).encode('utf-8')
            log(f"DEBUG FINAL SEND: {json.dumps(clean_payload)}")
            
        except Exception as e:
            log(f"DEBUG JSON ERROR: {e}")

    try:
        resp = requests.post(url, headers=headers, data=data, proxies=PROXIES, timeout=300)
        
        if resp.status_code >= 400:
            log(f"GOOGLE REJECTED (HTTP {resp.status_code}): {resp.text}")
            
        if 'responses' in request.path and resp.status_code == 200:
            try:
                res_json = resp.json()
                content = res_json['choices'][0]['message']['content']
                # Формат для n8n AI Agent (Content Blocks)
                n8n_res = {
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "text", "text": content}]
                        }
                    ]
                }
                return Response(json.dumps(n8n_res), 200, {'Content-Type': 'application/json'})
            except Exception as e:
                log(f"TRANSFORM ERROR: {e}")
            
        return Response(resp.content, resp.status_code, {'Content-Type': 'application/json'})
    except Exception as e:
        return str(e), 500

@app.route('/embeddings', methods=['POST'])
@app.route('/v1/embeddings', methods=['POST'])
def emb():
    try:
        payload = request.get_json()
        inputs = payload.get('input', '')
        if isinstance(inputs, str): inputs = [inputs]
        results = []
        for text in inputs:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={G_KEY}"
            resp = requests.post(url, json={"model":"models/gemini-embedding-2","content":{"parts":[{"text":text}]}}, proxies=PROXIES, timeout=60)
            if resp.status_code == 200:
                val = resp.json().get('embedding', {}).get('values', [])
                results.append({"object": "embedding", "embedding": val[:768], "index": len(results)})
            else: return Response(resp.content, resp.status_code)
        return Response(json.dumps({"object": "list", "data": results, "model": "gemini-embedding-2", "usage": {"total_tokens": 0}}), 200, {'Content-Type':'application/json'})
    except Exception as e: return Response(str(e), 500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
