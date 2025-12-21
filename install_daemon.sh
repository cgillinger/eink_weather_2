#!/bin/bash
# E-Paper Weather Daemon Installation Script
# Säker installation med konflikt-kontroll

set -e

echo "🚀 Installerar E-Paper Weather Daemon..."
echo "   Konverterar från cron till kontinuerlig daemon"

# Kontrollera att vi är i rätt katalog
if [ ! -f "main_daemon.py" ]; then
    echo "❌ main_daemon.py saknas. Kör från projektets root-katalog."
    exit 1
fi

if [ ! -f "config.json" ]; then
    echo "❌ config.json saknas. Kontrollera att du är i epaper_weather-mappen."
    exit 1
fi

# FINAL SAFETY CHECK: Bekräfta att cron redan är stoppad
echo "🔍 FINAL SÄKERHETSKONTROLL..."
echo "📋 Kontrollerar att cron är stoppad:"
if crontab -l 2>/dev/null | grep -E "(weather|epaper|main\.py)" >/dev/null; then
    echo "❌ KRITISKT FEL: Cron-jobs fortfarande aktiva!"
    echo "   Detta orsakar konflikter med daemon. Kör först:"
    echo "   crontab -l | grep -v 'main.py' | grep -v 'epaper' | crontab -"
    exit 1
else
    echo "✅ Inga cron-jobs aktiva - säkert att fortsätta"
fi

# Kontrollera att inga gamla main.py-processer körs
echo "🔍 Kontrollerar aktiva processer:"
if pgrep -f "python.*main\.py" >/dev/null; then
    echo "❌ VARNING: main.py-process upptäckt!"
    echo "   Stoppar aktiva processer..."
    pkill -f "python.*main\.py" || true
    sleep 2
    if pgrep -f "python.*main\.py" >/dev/null; then
        echo "❌ Kunde inte stoppa main.py-processer. Kontrollera manuellt."
        exit 1
    fi
fi
echo "✅ Inga main.py-processer körs"

# Skapa systemd-mapp om den inte finns
echo "📁 Förbereder systemd-filer..."
if [ ! -d "systemd" ]; then
    mkdir -p systemd
    echo "📁 Skapade systemd-mapp"
fi

# Spara service-fil från artifakt
echo "💾 Skapar systemd service-fil..."
cat > systemd/epaper-weather.service << 'EOF'
[Unit]
Description=E-Paper Weather Display Daemon
Documentation=E-Paper Weather Station with Netatmo + SMHI + Smart Updates
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=chris
Group=chris
WorkingDirectory=/home/chris/epaper_weather
ExecStart=/usr/bin/python3 /home/chris/epaper_weather/main_daemon.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONPATH=/home/chris/epaper_weather
Environment=HOME=/home/chris

# Security
NoNewPrivileges=true
PrivateTmp=true

# Resource limits
MemoryMax=256M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service-fil skapad: systemd/epaper-weather.service"

# Kopiera systemd service
echo "📦 Installerar systemd service..."
sudo cp systemd/epaper-weather.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ Service installerad i systemd"

# Aktivera service (auto-start vid boot)
echo "🔄 Aktiverar daemon för auto-start..."
sudo systemctl enable epaper-weather.service
echo "✅ Daemon aktiverad för auto-start vid boot"

# Starta service
echo "▶️ Startar daemon..."
sudo systemctl start epaper-weather.service
echo "✅ Daemon startad"

# Vänta lite och kontrollera status
echo "⏳ Väntar 3 sekunder och kontrollerar status..."
sleep 3

# Visa status
echo ""
echo "📊 DAEMON STATUS:"
if sudo systemctl is-active epaper-weather >/dev/null; then
    echo "✅ Daemon KÖR"
    echo ""
    echo "📋 Detaljer:"
    sudo systemctl status epaper-weather --no-pager -l | head -20
else
    echo "❌ Daemon körs inte!"
    echo ""
    echo "🔍 Status detaljer:"
    sudo systemctl status epaper-weather --no-pager -l
    echo ""
    echo "🔍 Kontrollera loggar:"
    echo "sudo journalctl -u epaper-weather -n 20"
    exit 1
fi

echo ""
echo "🎉 INSTALLATION KLAR!"
echo ""
echo "🔧 ANVÄNDBARA KOMMANDON:"
echo "  Status:      sudo systemctl status epaper-weather"
echo "  Loggar:      sudo journalctl -u epaper-weather -f"
echo "  Starta:      sudo systemctl start epaper-weather"
echo "  Stoppa:      sudo systemctl stop epaper-weather"
echo "  Restart:     sudo systemctl restart epaper-weather"
echo "  Avaktivera:  sudo systemctl disable epaper-weather"
echo ""
echo "📊 REALTIDS-LOGGAR (Ctrl+C för att avsluta):"
echo "sudo journalctl -u epaper-weather -f"
echo ""
echo "🎯 Daemon körs nu kontinuerligt och uppdaterar E-Paper display smart!"
echo "💤 Skärmen uppdateras endast vid förändring + 30-min watchdog"
echo "🔄 Auto-restart vid fel, auto-start vid reboot"