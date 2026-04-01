#!/usr/bin/env python3
"""
SMHI Vindparameter-test - Upptäck vilka vindbyar-parametrar som finns
Uppdaterad för SNOW1gv1 API (ersätter PMP3gv2)
Kör detta för att se exakt vilka parametrar SMHI erbjuder
"""

import requests
import json

def test_smhi_wind_parameters():
    """Testa vilka vindrelaterade parametrar SMHI verkligen har"""

    # Stockholms koordinater från config.json
    lat = 59.3293
    lon = 18.0686

    url = f"https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{lon}/lat/{lat}/data.json"

    print("🔍 Testar SMHI SNOW1gv1 API för vindbyar-parametrar...")
    print(f"📍 Stockholm: {lat}, {lon}")
    print(f"🌐 URL: {url}")
    print()

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"❌ HTTP fel: {response.status_code}")
            return False

        data = response.json()
        # SNOW1gv1: flat data object instead of parameters array
        params = data['timeSeries'][0]['data']

        print("📊 ALLA SMHI PARAMETRAR:")
        for name, value in params.items():
            print(f"  {name}: {value}")

        print("\n🌬️ VINDRELATERADE PARAMETRAR:")
        wind_params = {}
        for name, value in params.items():
            if any(keyword in name.lower() for keyword in ['wind', 'gust']):
                wind_params[name] = value
                print(f"  ✅ {name}: {value}")

        print(f"\n🎯 HITTADE {len(wind_params)} VINDRELATERADE PARAMETRAR")

        print("\n🔍 SPECIFIKT TEST - SÖKTA PARAMETRAR:")
        search_candidates = ['wind_speed', 'wind_from_direction', 'wind_speed_of_gust']

        found_params = {}
        for candidate in search_candidates:
            if candidate in params:
                found_params[candidate] = params[candidate]
                print(f"  ✅ {candidate}: {params[candidate]}")
            else:
                print(f"  ❌ {candidate}: INTE HITTAD")

        print(f"\n📋 SAMMANFATTNING:")
        print(f"  📊 Totalt parametrar: {len(params)}")
        print(f"  🌬️ Vindrelaterade: {len(wind_params)}")
        print(f"  ✅ Bekräftat fungerande: {len(found_params)}")

        if 'wind_speed' in found_params and 'wind_from_direction' in found_params:
            print(f"  🎯 Grundläggande vinddata: ✅ FINNS")
            print(f"     - Vindstyrka (wind_speed): {found_params['wind_speed']} m/s")
            print(f"     - Vindriktning (wind_from_direction): {found_params['wind_from_direction']}°")

        if 'wind_speed_of_gust' in found_params:
            gust_val = found_params['wind_speed_of_gust']
            print(f"  💨 VINDBYAR: ✅ FINNS som parameter 'wind_speed_of_gust' = {gust_val} m/s")

            # Beräkna ratio
            if 'wind_speed' in found_params and found_params['wind_speed'] > 0:
                ratio = gust_val / found_params['wind_speed']
                print(f"     - Gust/Wind ratio: {ratio:.2f} ({'Normal' if 1.1 <= ratio <= 2.5 else 'Ovanlig'})")
        else:
            print(f"  💨 VINDBYAR: ❌ INTE HITTADE")
            print(f"     - Rekommendation: Visa inte parentesen")
            print(f"     - Format: '8.5 m/s' (utan vindby-info)")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Nätverksfel: {e}")
        return False
    except Exception as e:
        print(f"❌ Fel: {e}")
        return False

if __name__ == "__main__":
    success = test_smhi_wind_parameters()
    if success:
        print("\n✅ Test slutfört - nu vet vi vilka parametrar SMHI har!")
    else:
        print("\n❌ Test misslyckades - kontrollera nätverksanslutning")
