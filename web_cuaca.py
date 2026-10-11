
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import requests
import json
import html
import os
from datetime import datetime, timedelta

URL = "https://api.open-meteo.com/v1/forecast"

PARAMS = {
    "latitude": -6.9219,
    "longitude": 107.6069,
    "timezone": "Asia/Jakarta",
    "past_days": 7,
    "forecast_days": 3,
    "current": (
        "temperature_2m,relative_humidity_2m,"
        "precipitation,rain,weather_code"
    ),
    "daily": (
        "temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,precipitation_probability_max,"
        "weather_code"
    )
}

def klasifikasi_hujan(mm):
    if mm == 0:
        return "Tidak ada hujan"
    elif mm <= 5:
        return "Hujan ringan"
    elif mm <= 20:
        return "Hujan sedang"
    return "Hujan tinggi"

def ambil_data():
    response = requests.get(URL, params=PARAMS, timeout=20)
    response.raise_for_status()
    return response.json()

def buat_halaman(data):
    current = data["current"]
    daily = data["daily"]
    today = current["time"][:10]

    # Tujuh hari sebelum hari ini
    histori = [
        (tanggal, hujan)
        for tanggal, hujan in zip(
            daily["time"], daily["precipitation_sum"]
        )
        if tanggal < today
    ][-7:]

    total = sum(hujan or 0 for _, hujan in histori)
    puncak = max(histori, key=lambda item: item[1] or 0) if histori else (today, 0)
    maksimum = max([h or 0 for _, h in histori], default=0) or 1

    # Dua hari setelah hari ini
    ramalan = [
        i for i, tanggal in enumerate(daily["time"])
        if tanggal > today
    ][:2]

    def kartu_ramalan(i):
        tanggal = daily["time"][i]
        hujan = daily["precipitation_sum"][i] or 0
        peluang = daily["precipitation_probability_max"][i]
        return f"""
        <div class="forecast">
          <b>{tanggal}</b>
          <h2>{daily['temperature_2m_max'][i]}°C</h2>
          <p>Suhu minimum: {daily['temperature_2m_min'][i]}°C</p>
          <p>Hujan: {hujan} mm</p>
          <p>Peluang hujan: {peluang}%</p>
          <small>{klasifikasi_hujan(hujan)}</small>
        </div>"""

    bars = ""
    for tanggal, hujan in histori:
        nilai = hujan or 0
        lebar = nilai / maksimum * 100
        bars += f"""
        <div class="bar-row">
          <span>{tanggal[5:]}</span>
          <div class="track">
            <div class="bar" style="width:{lebar}%"></div>
          </div>
          <b>{nilai} mm</b>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="1800">
<title>Cuaca Bandung</title>
<style>
* {{ box-sizing:border-box; }}
body {{
  margin:0; padding:18px; background:#edf5ff;
  font-family:Arial,sans-serif; color:#183653;
}}
main {{ max-width:650px; margin:auto; }}
header {{ padding:8px 4px 18px; }}
h1 {{ margin-bottom:5px; }}
p {{ line-height:1.5; }}
.card {{
  background:white; padding:20px; border-radius:20px;
  margin:14px 0; box-shadow:0 4px 16px #174a7e12;
}}
.hero {{ background:#2367ad; color:white; }}
.temp {{ font-size:54px; font-weight:bold; margin:12px 0; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.metric {{ background:#f0f6ff; padding:13px; border-radius:12px; }}
.metric b {{ display:block; font-size:20px; margin-top:7px; }}
.forecasts {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
.forecast {{ background:#f0f6ff; padding:12px; border-radius:14px; }}
.forecast h2 {{ margin:12px 0; }}
.bar-row {{
  display:grid; grid-template-columns:52px 1fr 55px;
  gap:8px; align-items:center; margin:13px 0; font-size:12px;
}}
.track {{ background:#e1eaf5; height:12px; border-radius:10px; overflow:hidden; }}
.bar {{ height:100%; background:#3289dc; border-radius:10px; }}
small,.note {{ color:#63788d; }}
.hero small {{ color:#e5f2ff; }}
footer {{ font-size:12px; padding:12px 3px; }}
</style>
</head>
<body>
<main>
<header>
  <h1>🌦️ Cuaca Bandung</h1>
  <p>Monitoring cuaca dan analisis curah hujan</p>
</header>

<section class="card hero">
  <p>Cuaca saat ini · Bandung</p>
  <div class="temp">{current['temperature_2m']}°C</div>
  <p>Kode cuaca: {current['weather_code']}</p>
  <div class="grid">
    <div class="metric">Kelembapan
      <b>{current['relative_humidity_2m']}%</b>
    </div>
    <div class="metric">Curah hujan saat ini
      <b>{current['precipitation']} mm</b>
    </div>
  </div>
  <p><small>Waktu data: {current['time']}</small></p>
</section>

<section class="card">
  <h2>📅 Prakiraan 2 Hari</h2>
  <div class="forecasts">
    {''.join(kartu_ramalan(i) for i in ramalan)}
  </div>
</section>

<section class="card">
  <h2>🌧️ Analisis 7 Hari Terakhir</h2>
  <p>Total curah hujan: <b>{round(total, 2)} mm</b></p>
  <p>Hari dengan hujan tertinggi: <b>{puncak[0]}</b>
     ({puncak[1]} mm)</p>
  <p>Klasifikasi puncak: <b>{klasifikasi_hujan(puncak[1] or 0)}</b></p>
  <hr>
  {bars}
</section>

<footer>
  Sumber: Open-Meteo API · Data model cuaca, bukan pengukuran
  langsung stasiun. Kategori hujan merupakan aturan sederhana
  untuk demonstrasi, bukan standar peringatan resmi.
</footer>
</main>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = ambil_data()
            halaman = buat_halaman(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(halaman)))
            self.end_headers()
            self.wfile.write(halaman)
        except Exception as error:
            pesan = (
                "<h2>Data cuaca belum dapat dimuat</h2>"
                "<p>Periksa koneksi internet, lalu muat ulang halaman.</p>"
                "<pre>" + html.escape(str(error)) + "</pre>"
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(pesan)

    def log_message(self, format, *args):
        print(args[0])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print("Aplikasi cuaca berjalan!")
    print("Buka browser: http://127.0.0.1:8000")
    print("Tekan CTRL+C untuk menghentikan aplikasi.")
    server.serve_forever()
