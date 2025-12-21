#!/usr/bin/env python3
"""
E-Paper Weather Daemon - Restart Script
Enkelt skript för att starta om väder-daemonen
"""

import subprocess
import sys
import time

def run_command(command, description, timeout=30):
    """Kör systemkommando och visa resultat"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            print(f"✅ {description} - OK")
            return True
        else:
            print(f"❌ {description} - FEL:")
            print(f"   {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT efter {timeout}s (E-Paper displayen behöver tid)")
        return False
    except Exception as e:
        print(f"❌ {description} - OVÄNTAT FEL: {e}")
        return False

def force_stop_daemon():
    """Tvinga stopp av daemon om systemctl hänger sig"""
    print("🔧 Tvingar stopp av daemon-processer...")
    try:
        # Döda alla main_daemon.py processer
        subprocess.run("sudo pkill -f main_daemon.py", shell=True, timeout=5)
        time.sleep(2)
        print("✅ Daemon-processer stoppade")
        return True
    except Exception as e:
        print(f"❌ Kunde inte tvinga stopp: {e}")
        return False

def main():
    """Huvudfunktion för daemon-restart"""
    print("🚀 E-Paper Weather Daemon - Restart Script")
    print("=" * 50)
    
    # 1. Försök stoppa daemonen normalt (med längre timeout för E-Paper)
    if not run_command("sudo systemctl stop epaper-weather", "Stoppar daemon", timeout=30):
        print("⚠️ Systemctl timeout - försöker tvinga stopp...")
        if not force_stop_daemon():
            print("❌ Kunde inte stoppa daemon alls - fortsätter ändå...")
    
    # Kort paus för att låta allt stabiliseras
    time.sleep(3)
    
    # 2. Starta daemonen (med längre timeout för E-Paper initialisering)
    if not run_command("sudo systemctl start epaper-weather", "Startar daemon", timeout=45):
        print("❌ KRITISKT: Kunde inte starta daemon!")
        print("🔧 Försöker diagnostisera problemet...")
        
        # Diagnostisera
        print("\n🔍 DIAGNOSTIK:")
        subprocess.run("sudo systemctl status epaper-weather --no-pager -l", shell=True)
        print("\n📋 Senaste loggar:")
        subprocess.run("sudo journalctl -u epaper-weather -n 10", shell=True)
        sys.exit(1)
    
    # Längre paus för att låta daemonen starta ordentligt
    time.sleep(5)
    
    # 3. Kontrollera status
    print("\n📊 DAEMON STATUS:")
    subprocess.run("sudo systemctl status epaper-weather --no-pager -l", shell=True)
    
    # 4. Visa om daemonen körs
    print("\n🔍 KONTROLLERAR AKTIVITET:")
    try:
        result = subprocess.run("sudo systemctl is-active epaper-weather", 
                              shell=True, capture_output=True, text=True)
        status = result.stdout.strip()
        
        if status == "active":
            print("✅ Daemon KÖR - E-Paper kommer uppdateras inom 60-90 sekunder")
            print("📱 Nytt datumformat testas nu!")
        else:
            print(f"❌ Daemon körs inte (status: {status})")
            print("\n🔍 Visa loggar för felsökning:")
            print("sudo journalctl -u epaper-weather -n 20")
    except:
        print("⚠️ Kunde inte kontrollera daemon-status")
    
    # 5. Erbjud att visa loggar
    print("\n" + "=" * 50)
    print("🎯 DAEMON OMSTART KLAR!")
    print("\n📋 ANVÄNDBARA KOMMANDON:")
    print("  Status:       sudo systemctl status epaper-weather")
    print("  Loggar live:  sudo journalctl -u epaper-weather -f")
    print("  Stoppa:       sudo systemctl stop epaper-weather")
    print("  Restart igen: python3 restart.py")
    
    # Fråga om användaren vill se live-loggar
    try:
        response = input("\n📺 Vill du se live-loggar? (y/N): ").strip().lower()
        if response in ['y', 'yes', 'ja', 'j']:
            print("\n📺 Visar live-loggar (Ctrl+C för att avsluta):")
            subprocess.run("sudo journalctl -u epaper-weather -f", shell=True)
    except KeyboardInterrupt:
        print("\n👋 Avslutad av användare")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Avbrutet av användare")
    except Exception as e:
        print(f"\n❌ Oväntat fel: {e}")
        sys.exit(1)