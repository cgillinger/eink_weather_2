#!/usr/bin/env python3
"""
SMHI Vindparameter-test - Upptäck vilka vindbyar-parametrar som finns
Kör detta för att se exakt vilka parametrar SMHI erbjuder
"""

import requests
import json

def test_smhi_wind_parameters():
    """Testa vilka vindrelaterade parametrar SMHI verkligen har"""
    
    # Stockholms koordinater från config.json
    lat = 59.3293
    lon = 18.0686
    
    url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"
    
    print("🔍 Testar SMHI API för vindbyar-parametrar...")
    print(f"📍 Stockholm: {lat}, {lon}")
    print(f"🌐 URL: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"❌ HTTP fel: {response.status_code}")
            return False
            
        data = response.json()
        parameters = data['timeSeries'][0]['parameters']
        
        print("📊 ALLA SMHI PARAMETRAR:")
        for param in parameters:
            name = param['name']
            unit = param.get('unit', 'no_unit')
            value = param['values'][0]
            print(f"  {name}: {value} {unit}")
        
        print("\n🌬️ VINDRELATERADE PARAMETRAR:")
        wind_params = []
        for param in parameters:
            name = param['name'].lower()
            if any(keyword in name for keyword in ['w', 'wind', 'gust', 'vindy', 'vindby']):
                wind_params.append(param)
                unit = param.get('unit', 'no_unit')
                value = param['values'][0]
                print(f"  ✅ {param['name']}: {value} {unit}")
        
        print(f"\n🎯 HITTADE {len(wind_params)} VINDRELATERADE PARAMETRAR")
        
        print("\n🔍 SPECIFIKT TEST - SÖKTA PARAMETRAR:")
        search_candidates = ['ws', 'wd', 'wg', 'gust', 'wind_gust', 'vindby', 'ws_max', 'wg_max']
        
        found_params = {}
        for candidate in search_candidates:
            found = next((p for p in parameters if p['name'] == candidate), None)
            if found:
                found_params[candidate] = found['values'][0]
                print(f"  ✅ {candidate}: {found['values'][0]} {found.get('unit', 'no_unit')}")
            else:
                print(f"  ❌ {candidate}: INTE HITTAD")
        
        print(f"\n📋 SAMMANFATTNING:")
        print(f"  📊 Totalt parametrar: {len(parameters)}")
        print(f"  🌬️ Vindrelaterade: {len(wind_params)}")
        print(f"  ✅ Bekräftat fungerande: {len(found_params)}")
        
        if 'ws' in found_params and 'wd' in found_params:
            print(f"  🎯 Grundläggande vinddata: ✅ FINNS")
            print(f"     - Vindstyrka (ws): {found_params['ws']} m/s")
            print(f"     - Vindriktning (wd): {found_params['wd']}°")
        
        if any(param in found_params for param in ['wg', 'gust', 'wind_gust']):
            gust_param = next(param for param in ['wg', 'gust', 'wind_gust'] if param in found_params)
            print(f"  💨 VINDBYAR: ✅ FINNS som parameter '{gust_param}' = {found_params[gust_param]} m/s")
            
            # Beräkna ratio
            if 'ws' in found_params and found_params['ws'] > 0:
                ratio = found_params[gust_param] / found_params['ws']
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
