import os
import sys
from waitress import serve
from app import create_app
from config import APP_NAME

if sys.platform.startswith('win'):
    os.system(f'title {APP_NAME}')
else:
    sys.stdout.write(f"\x1b]2;{APP_NAME}\x07")

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"[{APP_NAME}] Running on http://0.0.0.0:{port}")
    serve(app, host='0.0.0.0', port=port, threads=8)
