# SMHI-observationsstationer – stadslista med reservstationer

**större svenska städer** och **flera lämpliga SMHI-stationer per stad** för appens funktion **”regnar senaste timmen”**.

- Varje stad har **minst två stationer**
- **Stockholm, Göteborg och Malmö har tre**
- Först anges **huvudstation**, därefter **reservstation(er)**
- Om stationen inte ligger i staden anges det inom parentes

---

## Större svenska städer

### Stockholm
- `98230` – Stockholm-Observatoriekullen A *(huvud)*
- `97100` – Tullinge A *(reserv)*
- `98490` – Svanberga A *(reserv)*

### Göteborg
- `71420` – Göteborg A *(huvud)*
- `71380` – Vinga A *(reserv)*
- `81050` – Måseskär A *(reserv)*

### Malmö
- `52350` – Malmö A *(huvud)*
- `62040` – Helsingborg A *(reserv)*
- `54290` – Skillinge A *(reserv)*

### Uppsala
- `97510` – Uppsala Aut *(huvud)*
- `97530` – Uppsala Flygplats *(reserv)*

### Västerås
- `96560` – Sala A *(huvud)*
- `98490` – Svanberga A *(reserv)*  
  → *Västerås (Sala / Svanberga)*

### Örebro
- `94190` – Kilsbergen-Suttarboda A *(huvud)*
- `93520` – Sunne A *(reserv)*  
  → *Örebro (Kilsbergen / Sunne)*

### Linköping
- `85240` – Linköping-Malmslätt *(huvud)*
- `86420` – Kolmården-Strömsfors A *(reserv)*

### Norrköping
- `86420` – Kolmården-Strömsfors A *(huvud)*
- `87140` – Harstena A *(reserv)*  
  → *Norrköping (Kolmården / Harstena)*

### Jönköping
- `84050` – Visingsö A *(huvud)*
- `74300` – Tomtabacken A *(reserv)*  
  → *Jönköping (Visingsö / Tomtabacken)*

### Helsingborg
- `62040` – Helsingborg A *(huvud)*
- `52350` – Malmö A *(reserv)*

### Lund
- `52350` – Malmö A *(huvud)*
- `54290` – Skillinge A *(reserv)*  
  → *Lund (Malmö / Skillinge)*

### Umeå
- `140460` – Holmön A *(huvud)*
- `138390` – Hemling A *(reserv)*  
  → *Umeå (Holmön / Hemling)*

### Gävle
- `107420` – Gävle A *(huvud)*
- `117430` – Kuggören A *(reserv)*

### Borås
- `73480` – Rångedala A *(huvud)*
- `84520` – Gårdsjö A *(reserv)*  
  → *Borås (Rångedala / Gårdsjö)*

### Sundsvall
- `127130` – Brämön A *(huvud)*
- `128390` – Lungö A *(reserv)*  
  → *Sundsvall (Brämön / Lungö)*

### Växjö
- `64510` – Växjö A *(huvud)*
- `63510` – Ljungby A *(reserv)*

### Karlstad
- `94390` – Daglösen A *(huvud)*
- `93520` – Sunne A *(reserv)*  
  → *Karlstad (Daglösen / Sunne)*

### Eskilstuna
- `96190` – Eskilstuna A *(huvud)*
- `97370` – Enköping *(reserv)*

### Halmstad
- `72090` – Ullared A *(huvud)*
- `63590` – Torup A *(reserv)*  
  → *Halmstad (Ullared / Torup)*

### Östersund
- `134410` – Föllinge A *(huvud)*
- `132170` – Storlien-Storvallen A *(reserv)*  
  → *Östersund (Föllinge / Storlien)*

### Trollhättan
- `82360` – Kroppefjäll-Granan A *(huvud)*
- `83420` – Naven A *(reserv)*  
  → *Trollhättan (Kroppefjäll / Naven)*

---

## Rekommendation

I appens konfiguration bör varje stad ha:
- **en prioriterad ordning** (huvud → reserv)
- möjlighet att falla tillbaka om en station saknar data

Detta ger stabil funktion även vid driftstörningar hos SMHI.

---
