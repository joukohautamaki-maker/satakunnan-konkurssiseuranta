import os
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
    """Luo Markdown-taulukon ilman tabulate-riippuvuutta."""
    if df.empty:
        return "_Ei dataa_\n"
    
    headers = list(df.columns)
    markdown_lines = []
    
    markdown_lines.append("| " + " | ".join(headers) + " |")
    markdown_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    for _, row in df.iterrows():
        row_str = [str(val).replace("\n", " ") for val in row.values]
        markdown_lines.append("| " + " | ".join(row_str) + " |")
        
    return "\n".join(markdown_lines)

def fetch_statfin_bankruptcies():
    print("Haetaan konkurssitilastoja Tilastokeskuksen rajapinnasta...")
    
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
        "response": {
            "format": "json-stat2"
        }
    }

    records = []
    
    try:
        res = requests.post(STATFIN_API_URL, json=query, timeout=30)
        if res.status_code == 200:
            json_data = res.json()
            dimension = json_data.get("dimension", {})
            values = json_data.get("value", [])
            
            munis = list(dimension.get("Alue", {}).get("category", {}).get("label", {}).values())
            months = list(dimension.get("Kuukausi", {}).get("category", {}).get("label", {}).values())
            
            idx = 0
            for m in munis:
                for mo in months:
                    val = values[idx] if idx < len(values) else 0
                    if val is not None and val > 0:
                        records.append({
                            "Kunta": m,
                            "Kuukausi": mo,
                            "Konkurssien Määrä": int(val)
                        })
                    idx += 1
        else:
            print(f"StatFin API palautti koodin {res.status_code}")
    except Exception as e:
        print(f"Virhe haettaessa StatFin-dataa: {e}")

    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=["Kunta", "Kuukausi", "Konkurssien Määrä"])
        
    return df

def generate_visualizations(df):
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Kuukausittainen kaavio
    plt.figure(figsize=(10, 6))
    if not df.empty and "Konkurssien Määrä" in df.columns and df["Konkurssien Määrä"].sum() > 0:
        monthly_sum = df.groupby("Kuukausi")["Konkurssien Määrä"].sum()
        ax = monthly_sum.plot(kind="bar", color="#1f77b4", edgecolor="#0d3b66", linewidth=1.2)
        plt.title("Konkurssien määrä kuukausittain (1.1.2026 alkaen)\nSeurattavat 12 kuntaa", fontsize=11, pad=15)
        plt.xlabel("Kuukausi", fontsize=11)
        plt.ylabel("Konkurssit (kpl)", fontsize=11)
        plt.xticks(rotation=0)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        
        for p in ax.patches:
            if p.get_height() > 0:
                ax.annotate(str(int(p.get_height())), 
                            (p.get_x() + p.get_width() / 2., p.get_height()), 
                            ha='center', va='bottom', fontsize=10, fontweight='bold', xytext=(0, 3), 
                            textcoords='offset points')
    else:
        plt.text(0.5, 0.5, "Ei rekisteröityjä konkursseja valitulta ajalta.", horizontalalignment='center', verticalalignment='center', fontsize=12)
        plt.title("Konkurssit kuukausittain (2026)")

    plt.tight_layout()
    plt.savefig("reports/kuukausittaiset_konkurssit.png", dpi=300)
    plt.close()

    # Kuntakohtainen kaavio
    plt.figure(figsize=(10, 6))
    if not df.empty and "Konkurssien Määrä" in df.columns and df["Konkurssien Määrä"].sum() > 0:
        muni_sum = df.groupby("Kunta")["Konkurssien Määrä"].sum().sort_values(ascending=False)
        ax = muni_sum.plot(kind="barh", color="#2ca02c", edgecolor="#1b661b", linewidth=1.2)
        plt.title("Konkurssit kunnittain (1.1.2026 alkaen)", fontsize=11, pad=15)
        plt.xlabel("Konkurssit (kpl)", fontsize=11)
        plt.ylabel("Kunta", fontsize=11)
        plt.gca().invert_yaxis()
        plt.grid(axis="x", linestyle="--", alpha=0.7)
        
        for p in ax.patches:
            if p.get_width() > 0:
                ax.annotate(str(int(p.get_width())), 
                            (p.get_width(), p.get_y() + p.get_height() / 2.), 
                            ha='left', va='center', fontsize=10, fontweight='bold', xytext=(5, 0), 
                            textcoords='offset points')
    else:
        plt.text(0.5, 0.5, "Ei kuntakohtaista dataa saatavilla.", horizontalalignment='center', verticalalignment='center', fontsize=12)
        plt.title("Konkurssit kunnittain")

    plt.tight_layout()
    plt.savefig("reports/konkurssit_toimialoittain.png", dpi=300)
    plt.close()

def generate_markdown_report(df):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_md = f"""# Satakunnan ja lähialueiden konkurssiseuranta

**Päivitetty:** {now_str}  
**Aikaraja:** 1.1.2026 alkaen (Kumulatiivinen)  
**Seurattavat kunnat (12 kpl):** {', '.join(sorted(TARGET_MUNICIPALITIES))}

---

## 📊 Kuukausittainen kehitys

![Kuukausittaiset konkurssit](kuukausittaiset_konkurssit.png)

---

## 🏛️ Konkurssit kunnittain

![Konkurssit kunnittain](konkurssit_toimialoittain.png)

---

## 📋 Yhteenvetotaulukko

"""
    if not df.empty and "Konkurssien Määrä" in df.columns:
        total_count = df["Konkurssien Määrä"].sum()
        report_md += f"**Yhteensä rekisteröityjä konkursseja:** {total_count} kpl\n\n"
        report_md += df_to_markdown_custom(df) + "\n\n"
    else:
        report_md += "_Ei rekisteröityjä konkurssimerkintöjä valitulta ajanjaksolta._\n\n"

    report_md += "\n---\n*Raportti päivitetty automaattisesti Tilastokeskuksen StatFin-rajapinnasta.*"
    
    with open("reports/README.md", "w", encoding="utf-8") as f:
        f.write(report_md)

def main():
    ensure_directories()
    df = fetch_statfin_bankruptcies()
    
    df.to_csv("data/konkurssit_kumulatiivinen.csv", index=False, encoding="utf-8-sig")
    print(f"Tallennus valmis: {len(df)} riviä tiedostoon data/konkurssit_kumulatiivinen.csv")

    generate_visualizations(df)
    generate_markdown_report(df)

if __name__ == "__main__":
    main()
