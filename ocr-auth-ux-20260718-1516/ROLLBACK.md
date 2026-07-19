# Rollback

Restore files, then restart Apps Hub and AI OCR bridge:

cp telegram-apps/main.py.before /home/user/telegram-apps/main.py
cp telegram-apps/ocr-index.html.before /home/user/telegram-apps/static/ocr/index.html
cp telegram-apps/test_ocr_api.py.before /home/user/telegram-apps/tests/test_ocr_api.py
cp ai-ocr-service/app.py.before /home/user/n8n-docker/ai-ocr-service/app.py
cp ai-ocr-service/test_app.py.before /home/user/n8n-docker/ai-ocr-service/tests/test_app.py
docker restart apps-hub
systemctl --user restart ai-ocr-service
