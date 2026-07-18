#!/usr/bin/env python3
"""
Screenshot trigger for E-Paper Weather Daemon

Detta script:
- startar INTE rendering
- importerar INTE waveshare / GPIO
- orsakar INGA GPIO-konflikter

Det skickar ENBART SIGUSR1 till den redan körande daemonen,
som då sparar EXAKT den canvas som visas på E-Paper just då.
"""

import os
import signal
import subprocess
import sys


def find_daemon_pid():
    """
    Hitta PID för körande weather-daemon.
    Antagande: daemonen körs som python3.
    """
    try:
        # pgrep -f matchar på kommandoraden: träffar bara main_daemon.py.
        # "pidof python3" tog blint första python3-processen - kunde skicka
        # signalen till helt fel process (t.ex. web_server.py)
        output = subprocess.check_output(
            ["pgrep", "-f", "main_daemon.py"],
            text=True
        ).strip()

        return int(output.split()[0])

    except subprocess.CalledProcessError:
        return None


def main():
    pid = find_daemon_pid()

    if pid is None:
        print("❌ Ingen körande weather-daemon hittades")
        sys.exit(1)

    try:
        os.kill(pid, signal.SIGUSR1)
        print(f"📸 Screenshot begärd (SIGUSR1 skickad till PID {pid})")

    except PermissionError:
        print("❌ Saknar rättigheter att skicka signal (kör som samma användare)")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Kunde inte skicka screenshot-signal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

