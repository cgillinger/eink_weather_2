#!/usr/bin/env python3
"""
E-Paper Weather Display - Web Server
Serverar senaste screenshot för visning på iPhone/iPad via Safari genväg.

Funktioner:
- Visar senaste väder-screenshot i fullskärm
- Hela skärmen är klickbar för att uppdatera (refresh)
- Optimerad för iOS "Add to Home Screen" (standalone web app)
- Cache-busting för att alltid visa senaste bilden

Användning:
    python3 web_server.py

Lägg sedan till som genväg i Safari:
    1. Öppna http://<raspberry-pi-ip>:5000 i Safari
    2. Tryck på "Dela" → "Lägg till på hemskärmen"
    3. Tryck på genvägen för att öppna
    4. Tryck var som helst på skärmen för att uppdatera
"""

import os
import glob
from flask import Flask, send_file, Response
from datetime import datetime

app = Flask(__name__)

# Konfiguration
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screenshots')
PORT = 5000


def get_latest_screenshot():
    """Hitta senaste RGB screenshot (inte 1bit_)"""
    pattern = os.path.join(SCREENSHOT_DIR, '*.png')
    all_files = glob.glob(pattern)

    # Filtrera bort 1bit_ filer
    rgb_files = [f for f in all_files if not os.path.basename(f).startswith('1bit_')]

    if not rgb_files:
        return None

    # Returnera senast modifierade
    return max(rgb_files, key=os.path.getmtime)


@app.route('/')
def index():
    """Huvudsida med klickbar bild"""
    timestamp = int(datetime.now().timestamp() * 1000)

    html = f'''<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="apple-mobile-web-app-title" content="Väder">
    <title>E-Paper Väder</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: 100%;
            height: 100%;
            background: #fff;
            overflow: hidden;
            -webkit-tap-highlight-color: transparent;
        }}
        .container {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
        }}
        .weather-img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            transition: opacity 0.3s ease;
        }}
        .loading {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 18px;
            color: #333;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }}
        .container.refreshing .loading {{
            opacity: 1;
        }}
        .container.refreshing .weather-img {{
            opacity: 0.3;
        }}
        .spinner {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #ccc;
            border-top-color: #333;
            border-radius: 50%;
            margin-right: 10px;
            vertical-align: middle;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="container" onclick="refresh()">
        <img src="/image?t={timestamp}" class="weather-img" alt="Väder">
        <div class="loading"><span class="spinner"></span>Uppdaterar...</div>
    </div>
    <script>
        function refresh() {{
            document.querySelector('.container').classList.add('refreshing');
            setTimeout(function() {{
                window.location.href = '/?t=' + Date.now();
            }}, 800);
        }}
    </script>
</body>
</html>'''

    response = Response(html, mimetype='text/html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/image')
def image():
    """Servera senaste screenshot med no-cache headers"""
    screenshot = get_latest_screenshot()

    if not screenshot:
        # Returnera en placeholder om ingen bild finns
        return Response('Ingen screenshot tillgänglig', status=404)

    response = send_file(screenshot, mimetype='image/png')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


if __name__ == '__main__':
    print(f"🌤️  E-Paper Väder Web Server")
    print(f"📁 Screenshots: {SCREENSHOT_DIR}")
    print(f"🌐 Öppna i Safari: http://<din-ip>:{PORT}")
    print(f"📱 Lägg till på hemskärmen för app-känsla")
    print(f"👆 Tryck var som helst för att uppdatera")
    print()

    app.run(host='0.0.0.0', port=PORT, debug=False)
