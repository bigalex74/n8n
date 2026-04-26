import requests
import json

def test_bridge_translation():
    url = "http://127.0.0.1:5000/chat/completions"
    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
            {"role": "user", "content": "Переведи на русский: 안녕, 세상!"}
        ]
    }
    
    # Мы имитируем вызов от n8n. Ключ мост возьмет сам из Infisical.
    print(f"--- Sending request to Gemini Bridge (v30) ---")
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        translated_text = result['choices'][0]['message']['content']
        print(f"--- SUCCESS ---")
        print(f"Result: {translated_text}")
        return translated_text
    except Exception as e:
        print(f"--- FAILED ---")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

if __name__ == '__main__':
    test_bridge_translation()
