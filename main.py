import os
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

TARGET_MUNICIPALITIES = {
    "Kokemäki", "Harjavalta", "Nakkila", "Ulvila", "Pori",
    "Merikarvia", "Pomarkku", "Siikainen", "Karvia",
    "Kankaanpää", "Jämijärvi", "Eurajoki"
}

PRH_TR_API = "https://avoindata.prh.fi/tr/v1"
PRH_BIS_API = "https://avoindata.prh.fi/bis/v1"
START_DATE = "2026-01-01"

def ensure_directories():
    os.makedirs("reports", exist_ok=True)
    os.makedirs("data", exist_ok=True)

def fetch_bankruptcies():
    print(f"Haetaan PRH-rekisteri-ilmoituksia alkaen {START_DATE}...")
    
    # Haetaan kaupparekisterin merkintöjä / ilmoituksia
    params = {
        "totalResults": "true",
        "maxResults": 1000,
        "entryDateFrom": START_DATE
    }
    
    records = []
    
    try:
        res = requests.get(PRH_TR_API, params=params, timeout=30)
        if res.status_code != 200:
            print(f"TR API palautti tilakoodin {res.status_code}, kokeillaan vaihtoehtoista hakuasettelua...")
            res = requests.get(f"{PRH_BIS_API}?totalResults=true&maxResults=1000", timeout=30)
            
        data = res.json().get("results", [])
    except Exception as e:
        print(f"Virhe rajapintakyselyssä: {e}")
        data = []

    print(f"Löydetty {len(data)} merkintää. Suodatetaan kunnat ja konkurssitiedot...")

    processed_ids = set()

    for item in data:
        business_id = item.get("businessId")
        if not business_id or business_id in processed_ids:
            continue
            
        processed_ids.add(business_id)
        time.sleep(0.03)

        try:
            # Haetaan yrityksen tarkat perustiedot YTJ/PRH-rajapinnasta
            det_res = requests.get(f"{PRH_BIS_API}/{business_id}", timeout=10)
            if det_res.status_code == 200:
                det_json = det_res.json().get("results", [{}])[0]
                
                reg_office = det_json.get("registeredOffice", "")
                reg_office_clean = reg_office.strip().capitalize() if reg_office else ""

                # Tarkistetaan kuuluuko yritys seurattaviin kuntiin
                matched_muni = None
                for target in TARGET_MUNICIPALITIES:
                    if target.lower() == reg_office_clean.lower():
                        matched_muni = target
                        break

                if matched_muni:
                    # Tarkistetaan onko yrityksellä konkurssi-, selvitystila- tai rekisterimerkintä
                    liquidation = det_json.get("liquidations", [])
                    status_entries = det_json.get("registeredEntries", [])
                    
                    is_bankrupt = False
                    notice_date = item.get("registrationDate") or item.get("entryDate") or START_DATE
                    
                    if liquidation:
                        is_bankrupt = True
                    else:
                        for entry in status_entries:
                            desc = str(entry.get("description", "")).lower()
                            if "konkurssi" in desc or "selvitystila" in desc:
                                is_bankrupt = True
                                if entry.get("registrationDate"):
                                    notice_date = entry.get("registrationDate")
                                break

                    # Jos yrityksellä on merkintä tai tila kohdallaan, lisätään seurantaan
                    if is_bankrupt or len(liquidation) > 0:
                        b_lines = det_json.get("businessLines", [{}])
                        main_industry = b_lines[0].get("name", "Ei ilmoitettu") if b_lines else "Ei ilmoitettu"
                        
                        records.append({
                            "Y-tunnus": business_id,
                            "Yrityksen Nimi": det_json.get("name", "Tuntematon"),
                            "Kunta": matched_muni,
                            "Toimiala": main_industry,
                            "Rekisteröintipäivä": notice_date
                        })
        except Exception as err:
            continue

    df = pd.DataFrame(records)
    if not df.empty:
        df["Rekisteröintipäivä"] = pd.to_datetime(df["Rekisteröintipäivä"], errors='coerce').fillna(pd.to_datetime(START_DATE))
        df["Kuukausi"] = df["Rekisteröintipäivä"].dt.to_period("M").astype(str)
    return df

def generate_visualizations(df):
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    plt.figure(figsize=(10, 6))
    if not df.empty:
        monthly_counts = df.groupby("Kuukausi").size()
        ax = monthly_counts.plot(kind="bar", color="#1f77b4", edgecolor="#0d3b66", linewidth=1.2)
        plt.title(f"Konkurssien määrä kuukausittain (1.1.2026 alkaen)\nKohdekunnat ({len(TARGET_MUNICIPALITIES)} kpl)", fontsize=11, pad=15)
        plt.xlabel("Kuukausi", fontsize=11)
        plt.ylabel("Konkurssien määrä (kpl)", fontsize=11)
        plt.xticks(rotation=0)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        for p in ax.patches:
            if p.get_height() > 0:
                ax.annotate(str(int(p.get_height())), 
                            (p.get_x() + p.get_width() / 2., p.get_height()), 
                            ha='center', va='bottom', fontsize=10, fontweight='bold', xytext=(0, 3), 
                            textcoords='offset points')
    else:
        plt.text(0.5, 0.5, "Ei rekisteröityjä konkurssimerkintöjä valitulta ajalta.", horizontalalignment='center', verticalalignment='center', fontsize=12)
        plt.title("Konkurssien määrä kuukausittain (1.1.2026 alkaen)")

    plt.tight_layout()
    plt.savefig("reports/kuukausittaiset_konkurssit.png", dpi=300)
    plt.close()

    plt.figure(figsize=(10, 6))
    if not df.empty and "Toimiala" in df.columns:
        industry_counts = df["Toimiala"].value_counts().head(10)
        ax = industry_counts.plot(kind="barh", color="#2ca02c", edgecolor="#1b661b", linewidth=1.2)
        plt.title("Konkurssiin menneet yritykset toimialoittain (Top 10)", fontsize=11, pad=15)
        plt.xlabel("Määrä (kpl)", fontsize=11)
        plt.ylabel("Toimiala", fontsize=11)
        plt.gca().invert_yaxis()
        plt.grid(axis="x", linestyle="--", alpha=0.7)
        
        for p in ax.patches:
            if p.get_width() > 0:
                ax.annotate(str(int(p.get_width())), 
                            (p.get_width(), p.get_y() + p.get_height() / 2.), 
                            ha='left', va='center', fontsize=10, fontweight='bold', xytext=(5, 0), 
                            textcoords='offset points')
    else:
        plt.text(0.5, 0.5, "Ei toimialadataa saatavilla.", horizontalalignment='center', verticalalignment='center', fontsize=12)
        plt.title("Konkurssit toimialoittain")

    plt.tight_layout()
    plt.savefig("reports/konkurssit_toimialoittain.png", dpi=300)
    plt.close()

def generate_markdown_report(df):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_md = f"""# Satakunnan ja lähialueiden konkurssiseuranta

**Päivitetty:** {now_str}  
**Aikaraja:** 1.1.2026 alkaen (Kumulatiivinen)  
**Seurattavat kunnat ({len(TARGET_MUNICIPALITIES)} kpl):** {', '.join(sorted(TARGET_MUNICIPALITIES))}

---

## 📊 Kuukausittainen kehitys

![Kuukausittaiset konkurssit](kuukausittaiset_konkurssit.png)

---

## 🏭 Konkurssit toimialoittain

![Konkurssit toimialoittain](konkurssit_toimialoittain.png)

---

## 📋 Yhteenvetotaulukko

"""
    if not df.empty:
        total_count = len(df)
        report_md += f"**Yhteensä konkurssimerkintöjä:** {total_count} kpl\n\n"
        
        report_md += "### Konkurssit kunnittain\n\n"
        muni_summary = df["Kunta"].value_counts().reset_index()
        muni_summary.columns = ["Kunta", "Määrä (kpl)"]
        report_md += muni_summary.to_markdown(index=False) + "\n\n"

        report_md += "### Rekisteröidyt tapaukset\n\n"
        recent_df = df.sort_values(by="Rekisteröintipäivä", ascending=False)
        recent_display = recent_df[["Rekisteröintipäivä", "Y-tunnus", "Yrityksen Nimi", "Kunta", "Toimiala"]].copy()
        recent_display["Rekisteröintipäivä"] = recent_display["Rekisteröintipäivä"].dt.strftime("%Y-%m-%d")
        report_md += recent_display.to_markdown(index=False) + "\n\n"
    else:
        report_md += "_Ei rekisteröityjä konkurssimerkintöjä valitulta ajanjaksolta._\n\n"

    report_md += "\n---\n*Raportti luotu automaattisesti PRH:n avoimen rajapinnan pohjalta.*"
    
    with open("reports/README.md", "w", encoding="utf-8") as f:
        f.write(report_md)

def main():
    ensure_directories()
    df = fetch_bankruptcies()
    
    if not df.empty:
        df_to_save = df.copy()
        df_to_save["Rekisteröintipäivä"] = df_to_save["Rekisteröintipäivä"].dt.strftime("%Y-%m-%d")
        df_to_save.to_csv("data/konkurssit_kumulatiivinen.csv", index=False, encoding="utf-8-sig")
        print(f"Tallennettu {len(df)} riviä tiedostoon data/konkurssit_kumulatiivinen.csv")
    else:
        pd.DataFrame(columns=["Y-tunnus", "Yrityksen Nimi", "Kunta", "Toimiala", "Rekisteröintipäivä", "Kuukausi"]).to_csv("data/konkurssit_kumulatiivinen.csv", index=False, encoding="utf-8-sig")
        print("Ajo valmis, mutta yhtään ehtoihin täsmäävää konkurssia ei löytynyt.")

    generate_visualizations(df)
    generate_markdown_report(df)

if __name__ == "__main__":
    main()
