# Satakunnan Alueen Konkurssiseuranta-Agentti

Automaattinen GitHub Actions -työvuo ja Python-agentti, joka seuraa konkurssitilastoja PRH:n (Patentti- ja rekisterihallitus) avoimesta rajapinnasta (`avoindata.prh.fi`).

## 📍 Seurattavat kunnat
- **Satakunta & lähialueet:** Kokemäki, Harjavalta, Nakkila, Ulvila, Pori, Merikarvia, Pomarkku, Siikainen, Karvia, Kankaanpää, Jämijärvi ja Eurajoki.
- **Ajanjakso:** 1.1.2026 alkaen (kumulatiivinen).

## 🚀 Käyttöönotto GitHubissa

1. **Luo uusi GitHub-repositorio** (esim. `satakunta-konkurssiseuranta`).
2. **Lisää projektin tiedostot:**
   - `.github/workflows/bankruptcy_agent.yml`
   - `main.py`
   - `requirements.txt`
   - `README.md`
3. **Määritä GitHub-oikeudet (Workflow Permissions):**
   - Mene repositoriossa: `Settings` -> `Actions` -> `General`.
   - Kohdasta **Workflow permissions**, valitse: **Read and write permissions**.
   - Tallenna (`Save`).
4. **Käynnistys:**
   - Työvuo ajetaan automaattisesti joka kuukauden 1. päivä klo 06:00 UTC.
   - Voit myös käynnistää sen manuaalisesti kohdasta `Actions` -> `Satakunnan Konkurssiseuranta Agentti` -> `Run workflow`.

## 📊 Tuotettavat raportit
- **`reports/README.md`**: Automaattisesti päivittyvä Markdown-yhteenveto ja taulukot.
- **`reports/kuukausittaiset_konkurssit.png`**: Pylväsdiagrammi kuukausittaisista konkurssimääristä.
- **`reports/konkurssit_toimialoittain.png`**: Diagrammi konkurssiin menneiden yritysten toimialoista.
- **`data/konkurssit_kumulatiivinen.csv`**: Raakadata CSV-muodossa jatkoanalyysejä varten.
