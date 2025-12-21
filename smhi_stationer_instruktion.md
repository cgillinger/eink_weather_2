# SMHI‑observationsstationer – nybörjarguide


Du behöver **inte** kunna programmering eller API:er. Du börjar helt i **webbläsaren**. Terminalen används bara som ett **valfritt kontrollsteg** längre ner.

Syftet är att du själv ska kunna hitta rätt SMHI‑station för appens funktion **”regnar senaste timmen”**, även i framtiden när stationer kan ändras.

---

## 1. Vad använder appen egentligen?

Appen använder SMHI:s **observationsdata** för att avgöra:

> **Har det regnat under den senaste timmen?**

Det innebär:
- Nederbörd (inte prognos)
- Senaste timmen
- En fysisk mätstation

Det är allt. Temperatur, vind och prognoser hör inte hit.

---

## 2. Steg 1 – Hitta stationen via webben (viktigast)

Detta är **huvudmetoden** för nybörjare.

### 2.1 Öppna SMHI:s sida

1. Öppna din webbläsare
2. Gå till:

https://www.smhi.se/data/hitta-data-for-en-plats/ladda-ner-vaderobservationer

---

### 2.2 Välj rätt typ av data

På sidan:
- välj **Nederbörd** som parameter
- välj tidsupplösning **1 timme** (eller motsvarande)

Nu visas:
- en karta
- en lista med stationer

---

### 2.3 Leta upp din stad

1. Zooma in kartan till din stad
2. Klicka på stationer i eller nära staden
3. Notera **stationsnamnet**

Om stationen inte ligger exakt i staden:
- välj den som ligger **närmast geografiskt**

Exempel:
- Norrköping → station vid Kolmården
- Jönköping → station på Visingsö

Skriv då:

```
Norrköping (Kolmården‑Strömsfors)
```

---

### 2.4 Kontrollera att stationen rapporterar data

På SMHI‑sidan ser du om stationen:
- har mätvärden för nederbörd
- visar data för senaste timmen

Om du ser ett värde (även **0,0 mm**):
- stationen fungerar
- den är användbar för appen

---

## 3. Viktigt att förstå om nederbörd

- **0,0 mm** betyder: det regnade inte, men stationen fungerar
- Ett värde **större än 0** betyder: det regnade

Båda är lika viktiga för appen.

En station utan värde alls kan **inte** användas.

---

## 4. Steg 2 – Terminalen (valfritt men exakt)

Detta steg är **inte nödvändigt**, men bra om du vill dubbelkolla eller göra listor.

### 4.1 Lista alla stationer som fungerar just nu

```bash
curl -s "https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/7/station-set/all/period/latest-hour/data.json" \
| jq '.station[] | select(.value | length > 0) | {id: .key, name: .name}'
```

Detta visar:
- endast stationer som rapporterar nederbörd
- deras stations‑ID och namn

---

### 4.2 Kontrollera en specifik station

När du har ett stations‑ID, till exempel `98230`:

```bash
curl -s "https://opendata-download-metobs.smhi.se/api/version/latest/parameter/7/station/98230/period/latest-hour/data.json" | jq
```

Om du ser ett värde → stationen fungerar.

---

## 5. Varför detta arbetssätt är viktigt

SMHI‑stationer kan:
- sluta rapportera tillfälligt
- bytas ut
- flyttas eller få nytt namn

Genom att kunna detta flöde kan du **själv uppdatera appen**, utan att ändra kod.

---


