import os
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Kohdekunnat Satakunnassa ja lähialueilla
TARGET_MUNICIPALITIES = {
    "Kokemäki", "Harjavalta", "Nakkila", "Ulvila", "Pori",
    "Merikarvia", "Pomarkku", "Siikainen", "Karvia",
    "Kankaanpää", "Jämijärvi", "Eurajoki"
}

PRH_API_URL = "https://avoindata.prh.fi/tr/v1"
START_DATE = "2026-01-01"

def ensure_directories():
    os.makedirs("reports", exist_ok=True)
    os.makedirs("data", exist_ok=True)

def fetch_bankruptcies(start_date=START_DATE):
    """Haetaan PRH:n avoimesta rajapinnasta rekisteröidyt ilmoitukset alkaen start_date."""
    print(f"Haetaan PRH-dataa alkaen {start_date}...")
    params = {
        "totalResults": "true",
        "maxResults": 1000,
        "companyRegistrationFrom": start_date
    }
    
    try:
        response = requests.get(PRH_API_URL, params=params, timeout=30)
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception as e:
        print(f"Virhe haettaessa ilmoituksia PRH-rajapinnasta: {e}")
        results = []

    records = []
    print(f"Löydetty yhteensä {len(results)} ilmoitusta PRH:sta. Suodatetaan kohdekunnat...")

    for item in results:
        business_id = item.get("businessId")
        if not business_id:
            continue
            
        time.sleep(0.05) # Kohtelias viive API-kutsujen välissä
        
        try:
            det_res = requests.get(f"{PRH_API_URL}/{business_id}", timeout=10)
            if det_res.status_code == 200:
                det_data = det_res.json().get("results", [{}])[0]
                reg_office = det_data.get("registeredOffice", "")
                
                # Suodatetaan kohdekunnat
                reg_office_clean = reg_office.strip().capitalize() if reg_office else ""
                
                matched_muni = None
                for target in TARGET_MUNICIPALITIES:
                    if target.lower() == reg_office_clean.lower():
                        matched_muni = target
                        break

                if matched_muni:
                    b_lines = det_data.get("businessLines", [{}])
                    main_industry = b_lines[0].get("name", "Ei ilmoitettu") if b_lines else "Ei ilmoitettu"
                    company_name = det_data.get("name", "Tuntematon Nimi")
                    reg_date = item.get("registrationDate", "")

                    records.append({
                        "Y-tunnus": business_id,
                        "Yrityksen Nimi": company_name,
                        "Kunta": matched_muni,
                        "Toimiala": main_industry,
                        "Rekisteröintipäivä": reg_date
                    })
        except Exception as err:
            print(f"Virhe haettaessa tietoja Y-tunnukselle {business_id}: {err}")

    df = pd.DataFrame(records)
    if not df.empty:
        df["Rekisteröintipäivä"] = pd.to_datetime(df["Rekisteröintipäivä"])
        df["Kuukausi"] = df["Rekisteröintipäivä"].dt.to_period("M").astype(str)
    return df

def generate_visualizations(df):
    """Luo ja tallentaa tilastokuvaajat (kuukausittaiset määrät & toimialat)."""
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # 1. Kuukausittaiset konkurssit (Pylväsdiagrammi)
    plt.figure(figsize=(10, 6))
    if not df.empty:
        monthly_counts = df.groupby("Kuukausi").size()
        ax = monthly_counts.plot(kind="bar", color="#1f77b4", edgecolor="#0d3b66", linewidth=1.2)
        plt.title(f"Konkurssien määrä kuukausittain (1.1.2026 alkaen)\nKohdekunnat: {', '.join(sorted(TARGET_MUNICIPALITIES))}", fontsize=11, pad=15)
        plt.xlabel("Kuukausi", fontsize=11)
        plt.ylabel("Konkurssien määrä (kpl)", fontsize=11)
        plt.xticks(rotation=0)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        # Lisätään arvot pylväiden päälle
        for p in ax.patches:
            if p.get_height() > 0:
                ax.annotate(str(int(p.get_height())), 
                            (p.get_x() + p.get_width() / 2., p.get_height()), 
                            ha='center', va='bottom', fontsize=10, fontweight='bold', xytext=(0, 3), 
                            textcoords='offset points')
    else:
        plt.text(0.5, 0.5, "Ei rekisteröityjä konkursseja seuranta-ajalta.", horizontalalignment='center', verticalalignment='center', fontsize=12)
        plt.title("Konkurssien määrä kuukausittain (1.1.2026 alkaen)")

    plt.tight_layout()
    chart_path = "reports/kuukausittaiset_konkurssit.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()

    # 2. Toimialajakauma (Vaakapylväsdiagrammi)
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
    industry_chart_path = "reports/konkurssit_toimialoittain.png"
    plt.savefig(industry_chart_path, dpi=300)
    plt.close()

def generate_markdown_report(df):
    """Generoi automaattisen Markdown-raportin tuloksista."""
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
        
        # Kuntakohtainen yhteenveto
        report_md += "### Konkurssit kunnittain\n\n"
        muni_summary = df["Kunta"].value_counts().reset_index()
        muni_summary.columns = ["Kunta", "Määrä (kpl)"]
        report_md += muni_summary.to_markdown(index=False) + "\n\n"

        # Tuoreimmat tapaukset
        report_md += "### Tuoreimmat ilmoitukset\n\n"
        recent_df = df.sort_values(by="Rekisteröintipäivä", ascending=False).head(20)
        recent_display = recent_df[["Rekisteröintipäivä", "Y-tunnus", "Yrityksen Nimi", "Kunta", "Toimiala"]].copy()
        recent_display["Rekisteröintipäivä"] = recent_display["Rekisteröintipäivä"].dt.strftime("%Y-%m-%d")
        report_md += recent_display.to_markdown(index=False) + "\n\n"
    else:
        report_md += "_Ei rekisteröityjä konkurssimerkintöjä valitulta ajanjaksolta._\n\n"

    report_md += """
---
*Raportti luotu automaattisesti PRH:n avoimen rajapinnan (avoindata.prh.fi) pohjalta GitHub Actions -työvuon toimesta.*
"""
    
    with open("reports/README.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    
    print("Markdown-raportti luotu tiedostoon reports/README.md")

def main():
    ensure_directories()
    df = fetch_bankruptcies()
    
    # Tallenna raakadata CSV-tiedostoon
    if not df.empty:
        df_to_save = df.copy()
        df_to_save["Rekisteröintipäivä"] = df_to_save["Rekisteröintipäivä"].dt.strftime("%Y-%m-%d")
        df_to_save.to_csv("data/konkurssit_kumulatiivinen.csv", index=False, encoding="utf-8-sig")
        print("Data tallennettu: data/konkurssit_kumulatiivinen.csv")
    else:
        pd.DataFrame(columns=["Y-tunnus", "Yrityksen Nimi", "Kunta", "Toimiala", "Rekisteröintipäivä", "Kuukausi"]).to_csv("data/konkurssit_kumulatiivinen.csv", index=False, encoding="utf-8-sig")

    generate_visualizations(df)
    generate_markdown_report(df)
    print("Agentin suoritus valmis!")

if __name__ == "__main__":
    main()
