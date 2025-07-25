import requests
import time
import os
import csv
from datetime import datetime
import glob
import pandas as pd
import json


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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

DATAWRAPPER_API_TOKEN = os.getenv("DATAWRAPPER_API_TOKEN")
HEADERS_DW = {
    "Authorization": f"Bearer {DATAWRAPPER_API_TOKEN}",
    "Content-Type": "application/json"
}

# Städte in Deutschland
CITIES = ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig"]
CITY_COORDS = {
    "Berlin": [52.5200, 13.4050],
    "Hamburg": [53.5511, 9.9937],
    "Munich": [48.1351, 11.5820],
    "Cologne": [50.9375, 6.9603],
    "Frankfurt": [50.1109, 8.6821],
    "Stuttgart": [48.7758, 9.1829],
    "Düsseldorf": [51.2277, 6.7735],
    "Dortmund": [51.5136, 7.4653],
    "Essen": [51.4556, 7.0116],
    "Leipzig": [51.3397, 12.3731]
}

def get_ai_answer(model, content):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        },
        data=json.dumps({
            "model": model, # Optional
            "messages": [
            {
                "role": "user",
                "content": content
            }
            ]
        })
    )
    return response



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
# Table of contents generation
section_titles = [
    "Luftqualitätsindex (AQI) – Karte",
    "Luftqualitätsindex (AQI) in deutschen Städten",
    "Feinstaub PM2.5 Konzentration",
    "Feinstaub PM10 Konzentration",
    "Stickstoffdioxid (NO2)",
    "Ozon (O3)",
    "Schwefeldioxid (SO2)",
    "Kohlenmonoxid (CO)",
    "Luftqualitätskomponenten Vergleich",
    "Verlauf des AQI über Zeit"
]
section_ids = [
    "aqi-map",
    "aqi-bar",
    "pm25",
    "pm10",
    "no2",
    "o3",
    "so2",
    "co",
    "multi",
    "timeline"
]
# Add IDs to each section block
iframe_blocks_with_ids = []
for i, block in enumerate(iframe_blocks):
    # Add id to <section>
    block_with_id = block.replace('<section>', f'<section id="{section_ids[i]}">')
    iframe_blocks_with_ids.append(block_with_id)
# Table of contents HTML
contents_html = '<nav class="toc-nav">'
contents_html += '<h2 style="margin-top:0;color:#003366;">Inhalt</h2><ul style="list-style:none;padding-left:0;">'
for title, sid in zip(section_titles, section_ids):
    contents_html += f'<li style="margin-bottom:8px;"><a href="#{sid}" style="color:#003366;text-decoration:underline;">{title}</a></li>'
contents_html += '</ul></nav>'

# Status-Checks (wie bisher)
status_checks = []
try:
    test_resp = requests.get("https://api.api-ninjas.com/v1/airquality?city=Berlin", headers=HEADERS_NINJA, timeout=5)
    if test_resp.status_code == 200:
        status_checks.append({"name": "API Ninjas", "status": "OK", "desc": "Luftqualitätsdaten abrufbar"})
    else:
        status_checks.append({"name": "API Ninjas", "status": "Fehler", "desc": f"Statuscode: {test_resp.status_code}"})
except Exception as e:
    status_checks.append({"name": "API Ninjas", "status": "Fehler", "desc": str(e)})
try:
    test_dw = requests.get("https://api.datawrapper.de/v3/charts", headers=HEADERS_DW, timeout=5)
    if test_dw.status_code in [200, 401]:
        status_checks.append({"name": "Datawrapper API", "status": "OK", "desc": "Chart-API erreichbar"})
    else:
        status_checks.append({"name": "Datawrapper API", "status": "Fehler", "desc": f"Statuscode: {test_dw.status_code}"})
except Exception as e:
    status_checks.append({"name": "Datawrapper API", "status": "Fehler", "desc": str(e)})
chart_status = "OK" if len(iframe_blocks) > 0 else "Fehler"
status_checks.append({"name": "Diagramme", "status": chart_status, "desc": "Diagramme erfolgreich generiert" if chart_status == "OK" else "Keine Diagramme generiert"})
status_checks.append({"name": "Letztes Update", "status": timestamp, "desc": f"Zeitpunkt der letzten Aktualisierung: {timestamp}"})

# Write status to JSON
with open("status.json", "w", encoding="utf-8") as f:
    json.dump(status_checks, f, ensure_ascii=False, indent=2)

# Statusseite generieren
status_html_blocks = []
for check in status_checks:
    color = "#2ecc40" if check["status"] == "OK" else ("#ffdc00" if check["name"] == "Letztes Update" else "#ff4136")
    # 40 rectangles per status row
    rects = ''.join([f'<span class="status-rect" style="background:{color};" title="{check["desc"]}"></span>' for _ in range(47)])
    status_html_blocks.append(f'''
    <div class="status-item">
        <div style="font-weight:600;font-size:1.1em;color:#003366;margin-bottom:4px;">{check['name']}</div>
        <div class="status-bar">{rects}</div>
        <div style="font-size:0.95em;color:#555;margin-top:2px;">{check['desc']}</div>
    </div>
    ''')
status_html_blocks_str = ''.join(status_html_blocks)

status_page = f"""
<!DOCTYPE html>
<html lang=\"de\">
<head>
    <meta charset=\"UTF-8\">
    <title>Status – Luftqualitätsdaten</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <link rel=\"icon\" href=\"chart.png\">
    <style>
        body {{
            font-family: 'Inter', Arial, sans-serif;
            background: linear-gradient(120deg,#f5f7fa 0%,#c3cfe2 100%);
            margin: 0;
            min-height: 100vh;
        }}
        .container {{
            max-width: 600px;
            margin: 48px auto;
            background: #fff;
            border-radius: 18px;
            box-shadow: 0 4px 32px rgba(0,0,0,0.08);
            padding: 36px 32px 32px 32px;
        }}
        h1 {{
            text-align: center;
            color: #0c1754;
            font-size: 2.2em;
            margin-bottom: 12px;
        }}
        .status-list {{
            margin-top: 32px;
            display: flex;
            flex-direction: column;
            gap: 1.2em;
        }}
        .status-bar {{
            margin: 6px 0 8px 0;
            display: flex;
            gap: 2px;
        }}
        .status-rect {{
            display: inline-block;
            width: 10px;
            height: 18px;
            border-radius: 3px;
            background: #2ecc40;
            transition: background 0.2s;
        }}
        .status-item {{
            margin-bottom: 18px;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
        }}
        @media (max-width: 700px) {{
            .container {{
                padding: 16px 4px;
            }}
        }}
        .back-link {{
            display: block;
            text-align: center;
            margin-top: 32px;
            color: #003366;
            text-decoration: underline;
            font-size: 1.1em;
        }}
    </style>
</head>
<body>
    <div class=\"container\">
        <h1>Status</h1>
        <div class=\"status-list\">
            {status_html_blocks_str}
        </div>
        <a href=\"index.html\" class=\"back-link\">Zurück zur Hauptseite</a>
    </div>
</body>
</html>
"""

with open("status.html", "w", encoding="utf-8") as f:
    f.write(status_page)

# Interaktive Karte vorbereiten
map_markers = []
for entry in data_list:
    city = entry["city"]
    coords = CITY_COORDS.get(city)
    if coords:
        marker = {
            "city": city,
            "lat": coords[0],
            "lng": coords[1],
            "aqi": entry["aqi"],
            "pm25": entry["pm25"],
            "pm10": entry["pm10"],
            "co": entry["co"],
            "no2": entry["no2"],
            "so2": entry["so2"],
            "o3": entry["o3"]
        }
        map_markers.append(marker)
map_markers_json = json.dumps(map_markers)

# Interaktive Leaflet-Karte HTML Block
leaflet_map_html = f'''
<section id="interactive-map">
    <h2>Interaktive Karte: Luftqualitätsindex (AQI)</h2>
    <div id="leaflet-map" style="width:100%;height:500px;"></div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script>
    const markers = {map_markers_json};
    const map = L.map('leaflet-map').setView([51.1634, 10.4477], 6);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 18,
        attribution: '© OpenStreetMap'
    }}).addTo(map);
    markers.forEach(m => {{
        let color = m.aqi < 50 ? 'green' : m.aqi < 100 ? 'orange' : 'red';
        let marker = L.circleMarker([m.lat, m.lng], {{
            radius: 12,
            color: color,
            fillColor: color,
            fillOpacity: 0.7
        }}).addTo(map);
        marker.bindPopup(`<b>${{m.city}}</b><br>AQI: ${{m.aqi}}<br>PM2.5: ${{m.pm25}}<br>PM10: ${{m.pm10}}<br>CO: ${{m.co}}<br>NO₂: ${{m.no2}}<br>SO₂: ${{m.so2}}<br>O₃: ${{m.o3}}`);
    }});
    </script>
</section>
'''

# HTML-Seite für die Luftqualitätsdaten
# AI Summary für Website laden
try:
    with open("ai_summary.txt", "r", encoding="utf-8") as f:
        ai_summary_text = f.read()
except Exception:
    ai_summary_text = "(Keine Zusammenfassung verfügbar)"

# AI Summary HTML Block
ai_summary_html = f'''
<aside class="ai-summary-block">
    <h2>AI Zusammenfassung</h2>
    <div class="ai-summary-text">{ai_summary_text}</div>
</aside>
'''

iframe_html_blocks = []
for block in iframe_blocks_with_ids:
    import re
    block_fixed = re.sub(r'<iframe src="([^"]+)"', r'<iframe class="lazy-iframe" data-src="\1"', block)
    iframe_html_blocks.append(block_fixed)
iframe_html_blocks_str = ''.join(iframe_html_blocks)
# Interaktive Karte als ersten Block nach Inhaltsverzeichnis
all_html_blocks_str = leaflet_map_html + iframe_html_blocks_str
html_content = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Luftqualität in deutschen Städten</title>
    <meta name="description" content="Aktuelle Luftqualitätsdaten und Trends für deutsche Großstädte. Diagramme, Karten und Zeitverläufe.">
    <meta name="keywords" content="Luftqualität, AQI, Deutschland, Städte, Feinstaub, NO2, Ozon, Datawrapper, Umwelt, Diagramm, Karte">
    <meta name="author" content="Automatisch erzeugt mit Python und API Ninjas">
    <meta property="og:title" content="Luftqualität in deutschen Städten">
    <meta property="og:description" content="Vergleich und Verlauf der Luftqualität in deutschen Großstädten.">
    <meta property="og:type" content="website">
    <meta property="og:image" content="chart.png">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="chart.png">
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
            background: #0c1754;
            color: white;
            margin: 0;
            position: sticky;
            top: 0;
            z-index: 101;
        }}
        .toc-nav {{
            position: fixed;
            top: 100px;
            left: 200px;
            width: 220px;
            background: none;
            box-shadow: none;
            border-radius: 0;
            padding: 0 10px;
            z-index: 100;
        }}
        .main-content-wrapper {{
            display: flex;
            flex-direction: row;
            align-items: flex-start;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .main-content {{
            flex: 1;
            margin-left: 140px;
        }}
        .ai-summary-block {{
            width: 340px;
            margin-left: 32px;
            background: #f8fafc;
            border-radius: 12px;
            box-shadow: 0 0 10px rgba(0,0,0,0.07);
            padding: 24px 18px;
            position: sticky;
            top: 120px;
            height: fit-content;
        }}
        .ai-summary-block h2 {{
            color: #0c1754;
            font-size: 1.2em;
            margin-top: 0;
        }}
        .ai-summary-text {{
            color: #333;
            font-size: 1.05em;
            line-height: 1.6;
            white-space: pre-line;
        }}
        @media (max-width: 900px) {{
            .main-content-wrapper {{
                flex-direction: column;
            }}
            .ai-summary-block {{
                width: 100%;
                margin-left: 0;
                margin-top: 24px;
                position: static;
            }}
            .main-content {{
                margin-left: 0;
            }}
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
        @media (max-width: 600px) {{
            section {{
                max-width: 100%;
                padding: 5px 2px;
            }}
            iframe {{
                height: 300px !important;
            }}
        }}
        #leaflet-map {{
            width: 100%;
            height: 500px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.08);
        }}
        footer {{
            text-align: center;
            padding: 20px;
            background: #003366;
            color: white;
            margin-top: 40px;
        }}
        .lazy-iframe {{
            opacity: 0;
            transition: opacity 0.5s;
        }}
        .lazy-iframe.loaded {{
            opacity: 1;
        }}
        .main-content {{
            margin-left: 140px;
        }}
        @media (max-width: 900px) {{
            .main-content {{
                margin-left: 0;
            }}
        }}
        .status-section {{
            max-width: 900px;
            margin: 30px auto;
            background: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.08);
            border-radius: 10px;
            padding: 18px 24px;
        }}
        .status-list {{
            display: flex;
            flex-direction: column;
            gap: 0.5em;
        }}
        @media (max-width: 600px) {{
            .status-section {{
                padding: 8px 2px;
            }}
        }}
        .status-link {{
            display: block;
            text-align: center;
            margin: 18px auto 0 auto;
            color: #003366;
            text-decoration: underline;
            font-size: 1.1em;
        }}
    </style>
    <script>
    // Lazy loading for iframes
    document.addEventListener('DOMContentLoaded', function() {{
        const iframes = document.querySelectorAll('iframe[data-src]');
        const observer = new IntersectionObserver((entries, obs) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const iframe = entry.target;
                    iframe.src = iframe.dataset.src;
                    iframe.classList.add('loaded');
                    obs.unobserve(iframe);
                }}
            }});
        }}, {{ rootMargin: '100px' }});
        iframes.forEach(iframe => {{
            observer.observe(iframe);
        }});
    }});
    </script>
</head>
<body>
    <h1>Luftqualität in deutschen Großstädten (aktuell)</h1>
    <p style="text-align:center;">Letztes Update: {timestamp}</p>
    <a href="/status.html" class="status-link">Status &rarr;</a>
    {contents_html}
    <div class="main-content-wrapper">
        <div class="main-content">
            {all_html_blocks_str}
        </div>
        {ai_summary_html}
    </div>
    <footer>
        <p>Quellen: <a href="https://api-ninjas.com/api/airquality" style="color:white;">API Ninjas</a> &amp; <a href="https://www.datawrapper.de/" style="color:white;">Datawrapper</a></p>
        <p>&copy; 2025 Luftqualitätsdaten Deutschland</p>
    </footer>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("-------------Fertig-------------")
print("Website generated successfully!")

# Nach dem Sammeln der Daten, AI Summary generieren
summary_file = "ai_summary.txt"
if len(data_list) > 0:
    # Prompt für die Zusammenfassung
    cities_str = ", ".join([entry["city"] for entry in data_list])
    avg_aqi = sum([entry["aqi"] for entry in data_list]) / len(data_list)
    prompt = f"Fasse die Luftqualitätsdaten für folgende deutsche Großstädte zusammen: {cities_str}. Der durchschnittliche AQI beträgt {avg_aqi:.1f}. Erwähne Besonderheiten, Trends und gib einen kurzen Ausblick."
    try:
        ai_resp = get_ai_answer("google/gemini-2.0-flash-exp:free", prompt)
        resp_json = ai_resp.json()
        if "choices" in resp_json and resp_json["choices"]:
            ai_text = resp_json["choices"][0]["message"]["content"]
        else:
            print("OpenRouter Fehler/Antwort:", resp_json)
            ai_text = "(Fehler beim Generieren der Zusammenfassung)"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(ai_text)
    except Exception as e:
        print(f"Fehler beim Generieren der AI-Zusammenfassung: {e}")
        ai_text = "(Fehler beim Generieren der Zusammenfassung)"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(ai_text)
