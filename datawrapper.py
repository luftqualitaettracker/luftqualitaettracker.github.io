import requests
import time
import os
import csv
from datetime import datetime
import glob
import pandas as pd

# Ordner für Datenhistorie
os.makedirs("data", exist_ok=True)

# Zeitstempel für die Messung
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
date_str = datetime.now().strftime("%Y-%m-%d")
file_path = f"data/{date_str}.csv"

# Schreibe oder erweitere CSV-Datei
write_header = not os.path.exists(file_path)

# API Keys from environment variables
NINJA_API_KEY = os.getenv("NINJA_API_KEY")
HEADERS_NINJA = {"X-Api-Key": NINJA_API_KEY}

DATAWRAPPER_API_TOKEN = os.getenv("DATAWRAPPER_API_TOKEN")
HEADERS_DW = {
    "Authorization": f"Bearer {DATAWRAPPER_API_TOKEN}",
    "Content-Type": "application/json"
}

# Städte in Deutschland
CITIES = ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig"]

# Luftqualitätsdaten abrufen
def get_air_quality(city):
    url = f"https://api.api-ninjas.com/v1/airquality?city={city}"
    response = requests.get(url, headers=HEADERS_NINJA)
    response.raise_for_status()
    data = response.json()
    return {
        "city": city,
        "aqi": data["overall_aqi"],
        "pm25": data["PM2.5"]["concentration"],
        "pm10": data["PM10"]["concentration"],
        "co": data["CO"]["concentration"],
        "no2": data["NO2"]["concentration"],
        "so2": data["SO2"]["concentration"],
        "o3": data["O3"]["concentration"],
    }

# Daten sammeln
data_list = []
for city in CITIES:
    try:
        print(f"Abrufe Luftqualität für {city}...")
        result = get_air_quality(city)
        data_list.append(result)
        time.sleep(0.5)
    except Exception as e:
        print(f"Fehler bei {city}: {e}")

# Nach AQI sortieren
data_list.sort(key=lambda x: x["aqi"])

with open(file_path, "a", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    if write_header:
        writer.writerow(["timestamp", "city", "aqi", "pm25", "pm10", "co", "no2", "so2", "o3"])
    for entry in data_list:
        writer.writerow([
            timestamp,
            entry["city"],
            entry["aqi"],
            entry["pm25"],
            entry["pm10"],
            entry["co"],
            entry["no2"],
            entry["so2"],
            entry["o3"]
        ])

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# CSV vorbereiten
header = ["city", "aqi", "pm25", "pm10", "co", "no2", "so2", "o3"]
rows = [header]
for entry in data_list:
    row = [str(entry[col]) for col in header]
    rows.append(row)

csv_data = "\n".join([",".join(row) for row in rows])
print("CSV-Daten fertig")


charts_info = [
    ("Luftqualitätsindex (AQI) in deutschen Städten", "aqi"),
    ("Feinstaub PM2.5 Konzentration", "pm25"),
    ("Feinstaub PM10 Konzentration", "pm10"),
    ("Stickstoffdioxid (NO2)", "no2"),
    ("Ozon (O3)", "o3"),
    ("Schwefeldioxid (SO2)", "so2"),
    ("Kohlenmonoxid (CO)", "co"),
    ("Luftqualitätskomponenten Vergleich", "multi")
]

# speichern Chart-IDs pro Titel
iframe_blocks = []

# Die URLs wurden beim Chart-Upload erstellt, aber wir fangen sie jetzt ab
def create_and_publish_chart_with_return(title, columns, chart_type="d3-bars"):
    csv_header = ["city"] + columns
    rows_chart = [csv_header]
    for entry in data_list:
        row = [entry["city"]] + [str(entry[col]) for col in columns]
        rows_chart.append(row)
    csv_part = "\n".join([",".join(row) for row in rows_chart])

    # Chart erstellen
    resp = requests.post(
        "https://api.datawrapper.de/v3/charts",
        headers=HEADERS_DW,
        json={"title": title, "type": chart_type}
    )
    chart_id = resp.json()["id"]

    # CSV hochladen
    requests.put(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/data",
        headers={"Authorization": f"Bearer {DATAWRAPPER_API_TOKEN}", "Content-Type": "text/csv"},
        data=csv_part.encode("utf-8")
    )

    # Metadaten
    meta = {
        "metadata": {
            "describe": {
                "source-name": "API Ninjas",
                "source-url": "https://api-ninjas.com/api/airquality",
                "byline": "Automatisch erzeugt mit Python",
                "intro": f"{title} für deutsche Großstädte (aktuell)"
            },
            "visualize": {
                "x-axis": {"title": "Stadt"},
                "y-axis": {"title": "Wert"},
                "sharing": {"enabled": True}
            }
        }
    }
    requests.patch(f"https://api.datawrapper.de/v3/charts/{chart_id}", headers=HEADERS_DW, json=meta)

    # Veröffentlichen
    requests.post(f"https://api.datawrapper.de/v3/charts/{chart_id}/publish", headers=HEADERS_DW)

    print(f"✅ {title} veröffentlicht: https://datawrapper.dwcdn.net/{chart_id}/")
    return chart_id

# Charts
for title, col in charts_info:
    if col == "multi":
        chart_id = create_and_publish_chart_with_return(title, ["pm25", "pm10", "co", "no2", "so2", "o3"], chart_type="d3-bars-split")
    else:
        chart_id = create_and_publish_chart_with_return(title, [col])
    iframe_url = f"https://datawrapper.dwcdn.net/{chart_id}/1/"
    iframe_html = f"""
    <section>
        <h2>{title}</h2>
        <iframe src="{iframe_url}" scrolling="no" frameborder="0" style="width: 100%; height: 500px;"></iframe>
    </section>
    """
    iframe_blocks.append(iframe_html)

# Karten-Diagramm erstellen
def create_map_chart():
    title = "AQI nach Stadt auf Karte"
    map_key = "de.districts"
    csv_header = ["id", "value"]
    rows_map = [csv_header]
    for entry in data_list:
        # Datawrapper erwartet IDs wie "Berlin", "Hamburg", etc. für de.cities
        rows_map.append([entry["city"], str(entry["aqi"])])
    csv_map = "\n".join([",".join(row) for row in rows_map])

    # Karte erstellen
    resp = requests.post(
        "https://api.datawrapper.de/v3/charts",
        headers=HEADERS_DW,
        json={
            "title": title,
            "type": "d3-maps-choropleth",
            "metadata": {
                "visualize": {
                    "map-key": map_key,
                    "map-value": "value",
                    "label": "id",
                    "tooltip": {
                        "body": "{{id}}: AQI {{value}}"
                    }
                }
            }
        }
    )
    chart_id = resp.json()["id"]

    # CSV-Daten hochladen
    requests.put(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/data",
        headers={
            "Authorization": f"Bearer {DATAWRAPPER_API_TOKEN}",
            "Content-Type": "text/csv"
        },
        data=csv_map.encode("utf-8")
    )

    # Metadaten ergänzen
    meta = {
        "metadata": {
            "describe": {
                "source-name": "API Ninjas",
                "source-url": "https://api-ninjas.com/api/airquality",
                "byline": "Automatisch erzeugt mit Python",
                "intro": "Luftqualitätsindex (AQI) als Karte für deutsche Städte"
            },
            "visualize": {
                "colors": {
                    "custom": True,
                    "palette": "red-yellow-green",
                    "reverse": True
                },
                "sharing": {
                    "enabled": True
                }
            }
        }
    }
    requests.patch(f"https://api.datawrapper.de/v3/charts/{chart_id}", headers=HEADERS_DW, json=meta)

    # Veröffentlichen
    requests.post(f"https://api.datawrapper.de/v3/charts/{chart_id}/publish", headers=HEADERS_DW)

    print(f"🗺️ Karten-Chart veröffentlicht: https://datawrapper.dwcdn.net/{chart_id}/")
    return chart_id

# Karte erstellen
map_chart_id = create_map_chart()

# HTML-Block für Karte ergänzen
iframe_url = f"https://datawrapper.dwcdn.net/{map_chart_id}/1/"
iframe_html = f"""
<section>
    <h2>Luftqualitätsindex (AQI) – Karte</h2>
    <iframe src="{iframe_url}" scrolling="no" frameborder="0" style="width: 100%; height: 600px;"></iframe>
</section>
"""
iframe_blocks.insert(0, iframe_html)  # Karte als erstes Element auf der Seite

def create_aqi_timeline_chart():
    title = "AQI-Verlauf in deutschen Städten (letzte Tage)"

    # Alle Tagesdateien laden
    files = sorted(glob.glob("data/*.csv"))
    df_list = []
    for file in files:
        df = pd.read_csv(file)
        df_list.append(df)
    all_data = pd.concat(df_list)

    # Zeitreihe aufbauen: eine Zeile pro Zeit, Spalten = Städte
    pivot = all_data.pivot_table(index="timestamp", columns="city", values="aqi").reset_index()
    pivot = pivot.sort_values("timestamp")
    pivot.fillna("", inplace=True)

    # CSV-Daten für Datawrapper vorbereiten
    csv_data = ",".join(pivot.columns) + "\n"
    for _, row in pivot.iterrows():
        csv_data += ",".join(str(val) for val in row.values) + "\n"

    # Chart erstellen
    resp = requests.post(
        "https://api.datawrapper.de/v3/charts",
        headers=HEADERS_DW,
        json={"title": title, "type": "d3-lines"}
    )
    chart_id = resp.json()["id"]

    # CSV hochladen
    requests.put(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/data",
        headers={"Authorization": f"Bearer {DATAWRAPPER_API_TOKEN}", "Content-Type": "text/csv"},
        data=csv_data.encode("utf-8")
    )

    # Metadaten
    meta = {
        "metadata": {
            "describe": {
                "source-name": "API Ninjas",
                "source-url": "https://api-ninjas.com/api/airquality",
                "byline": "Automatisch erzeugt mit Python",
                "intro": f"AQI-Zeitverlauf deutscher Städte"
            },
            "visualize": {
                "x-axis": {"title": "Zeitpunkt"},
                "y-axis": {"title": "AQI"},
                "sharing": {"enabled": True}
            }
        }
    }
    requests.patch(f"https://api.datawrapper.de/v3/charts/{chart_id}", headers=HEADERS_DW, json=meta)

    # Veröffentlichen
    requests.post(f"https://api.datawrapper.de/v3/charts/{chart_id}/publish", headers=HEADERS_DW)
    print(f"📈 Verlauf-Chart veröffentlicht: https://datawrapper.dwcdn.net/{chart_id}/")
    return chart_id

# Verlauf-Chart einfügen
timeline_chart_id = create_aqi_timeline_chart()
iframe_url = f"https://datawrapper.dwcdn.net/{timeline_chart_id}/1/"
iframe_html = f"""
<section>
    <h2>Verlauf des AQI über Zeit</h2>
    <iframe src="{iframe_url}" scrolling="no" frameborder="0" style="width: 100%; height: 500px;"></iframe>
</section>
"""
iframe_blocks.append(iframe_html)

# html seite schreiben
html_content = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Luftqualität in deutschen Städten</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }}
        h1 {{
            text-align: center;
            padding: 20px;
            background: #003366;
            color: white;
            margin: 0;
        }}
        section {{
            margin: 30px auto;
            padding: 10px 20px;
            max-width: 900px;
            background: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h2 {{
            margin-top: 0;
            color: #003366;
        }}
    </style>
</head>
<body>
    <h1>Luftqualität in deutschen Großstädten (aktuell)</h1>
    <p style="text-align:center;">Letztes Update: {timestamp}</p>
    {''.join(iframe_blocks)}
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("-------------Fertig-------------")
print("Website generated successfully!")
