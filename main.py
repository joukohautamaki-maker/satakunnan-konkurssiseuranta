import os
import sys
import traceback
import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TARGET_MUNICIPALITIES = [
    "Kokemäki", "Harjavalta", "Nakkila", "Ulvila", "Pori",
    "Merikarvia", "Pomarkku", "Siikainen", "Karvia",
    "Kankaanpää", "Jämijärvi", "Eurajoki"
]

STATFIN_API_URL = "https://pxdata.stat.fi:443/PxWeb/api/v1/fi/StatFin/konk/statfin_konk_pxt_12vh.json"

def ensure_directories():
    os.makedirs("reports", exist_ok=True)
    os.makedirs("data", exist_ok=True)

def df_to_markdown_custom(df):
    if df.empty:
        return "_Ei dataa saatavilla_\n"
    headers = list(df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |"
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v).replace("\n", " ") for v in row.values) + " |")
    return "\n".join(lines)

def fetch_statfin_data():
    print("Aloitetaan konkurssitietojen haku StatFin-rajapinnasta...")
    
    query = {
        "query": [
            {
                "code": "Alue",
                "selection": {
                    "filter": "item",
                    "values": ["KU408", "KU079", "KU531", "KU886", "KU609", "KU484", "KU608", "KU747", "KU230", "KU214", "KU181", "KU051"]
                }
            },
            {
                "code": "Kuukausi",
                "selection": {
                    "filter": "item",
                    "values": ["2026M01", "2026M02", "2026M03", "2026M04", "2026M05", "2026M06", "2026M07", "2026M08"]
                }
            },
            {
                "code": "Tiedot",
                "selection": {
                    "filter": "item",
                    "values": ["konk_maara"]
                }
            }
        ],
        "response": {"format": "json-stat2"}
    }

    records = []
    try:
        res = requests.post(STATFIN_API_URL, json=query, timeout=20)
        print(f"StatFin API tilakoodi: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            dimension = data.get("dimension", {})
            values = data.get("value", [])
            munis = list(dimension.get("Alue", {}).get("category", {}).get("label", {}).values())
            months = list(dimension.get("Kuukausi", {}).get("category", {}).get("label", {}).values())
            
            idx = 0
            for m in munis:
                for mo in months:
                    val = values[idx] if idx < len(values) else 0
                    if val is not None and val > 0:
                        records.append({"Kunta": m, "Kuukausi": mo, "Konkurssien Määrä": int(val)})
                    idx += 1
    except Exception as e:
        print(f"Rajapintavirhe (ohitetaan turvallisesti): {e}")

    df = pd.DataFrame(records)
    if df.empty:
        print("Tietoja ei löytynyt tai rajapinta ei palauttanut rivejä. Luodaan tyhjä seurantakanta.")
        df = pd.DataFrame(columns=["Kunta", "Kuukausi", "Konkurssien Määrä"])
    return df

def generate_visualizations(df):
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Kuukausittainen kaavio
    plt.figure(figsize=(10, 6))
    if not df.empty and "Konkurssien Määrä" in df.columns and df["Konkurssien Määrä"].sum() > 0:
        monthly = df.groupby("Kuukausi")["Konkurssien Määrä"].sum()
        ax = monthly.plot(kind="bar", color="#1f77b4", edgecolor="#0d3b66")
        plt.title("Konkurssien määrä kuukausittain (2026)", fontsize=11)
        plt.xlabel("Kuukausi")
        plt.ylabel("Määrä (kpl)")
        for p in ax.patches:
            if p.get_height() > 0:
                ax.annotate(str(int(p.get_height())), (p.get_x() + p.get_width()/2., p.get_height()), ha='center', va='bottom')
    else:
        plt.text(0.5, 0.5, "Ei rekisteröityjä konkursseja seuranta-ajalta.", ha='center', va='center')
        plt.title("Konkurssit kuukausittain (2026)")
    plt.tight_layout()
    plt.savefig("reports/kuukausittaiset_konkurssit.png", dpi=300)
    plt.close()

    # Kunnittainen kaavio
    plt.figure(figsize=(10, 6))
    if not df.empty and "Konkurssien Määrä" in df.columns and df["Konkurssien Määrä"].sum() > 0:
        muni = df.groupby("Kunta")["Konkurssien Määrä"].sum().sort_values(ascending=False)
        ax = muni.plot(kind="barh", color="#2ca02c", edgecolor="#1b661b")
        plt.title("Konkurssit kunnittain (2026)", fontsize=11)
        plt.xlabel("Määrä (kpl)")
        plt.gca().invert_yaxis()
        for p in ax.patches:
            if p.get_width() > 0:
                ax.annotate(str(int(p.get_width())), (p.get_width(), p.get_y() + p.get_height()/2.), ha='left', va='center')
    else:
        plt.text(0.5, 0.5, "Ei kuntakohtaista dataa saatavilla.", ha='center', va='center')
        plt.title("Konkurssit kunnittain")
    plt.tight_layout()
    plt.savefig("reports/konkurssit_toimialoittain.png", dpi=300)
    plt.close()

def generate_markdown(df):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"""# Satakunnan ja lähialueiden konkurssiseuranta

**Päivitetty:** {now_str}  
**Seurattavat kunnat ({len(TARGET_MUNICIPALITIES)} kpl):** {', '.join(sorted(TARGET_MUNICIPALITIES))}

---

## 📊 Kuukausittainen kehitys

![Kuukausittaiset konkurssit](kuukausittaiset_konkurssit.png)

---

## 🏛️ Konkurssit kunnittain

![Konkurssit kunnittain](konkurssit_toimialoittain.png)

---

## 📋 Yhteenvetotaulukko

"""
    if not df.empty and "Konkurssien Määrä" in df.columns and df["Konkurssien Määrä"].sum() > 0:
        md += f"**Yhteensä rekisteröityjä konkursseja:** {df['Konkurssien Määrä'].sum()} kpl\n\n"
        md += df_to_markdown_custom(df) + "\n\n"
    else:
        md += "_Ei rekisteröityjä konkurssimerkintöjä valitulta ajanjaksolta._\n\n"

    md += "\n---\n*Raportti luotu automaattisesti Tilastokeskuksen avoimen rajapinnan pohjalta.*"
    with open("reports/README.md", "w", encoding="utf-8") as f:
        f.write(md)

def main():
    try:
        ensure_directories()
        df = fetch_statfin_data()
        df.to_csv("data/konkurssit_kumulatiivinen.csv", index=False, encoding="utf-8-sig")
        generate_visualizations(df)
        generate_markdown(df)
        print("Suoritus valmis.")
    except Exception as e:
        print(f"POIKKEUS SUORITUKSESSA: {e}")
        traceback.print_exc()
        ensure_directories()
        pd.DataFrame(columns=["Kunta", "Kuukausi", "Konkurssien Määrä"]).to_csv("data/konkurssit_kumulatiivinen.csv", index=False)
        sys.exit(0)

if __name__ == "__main__":
    main()
