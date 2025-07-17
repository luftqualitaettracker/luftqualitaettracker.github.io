#!/bin/sh

echo "🔄 Starte initialen Datenerhebungslauf..."
python3 /datawrapper.py

(
  while true; do
    echo "🕒 Warte 3 Stunden bis zum nächsten Lauf..."
    sleep 1080  # 3 Stunden = 3*60*60 Sekunden
    echo "🔄 Starte erneuten Datenerhebungslauf..."
    python3 /datawrapper.py
  done
) &

echo "🚀 Starte NGINX Webserver..."
nginx -g 'daemon off;'
