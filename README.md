# 🔍 CLI Troubleshooter

Zaawansowane narzędzie do diagnostyki sieci z interfejsem CLI i dashboardem webowym, zasilane przez **Claude AI** (Anthropic). Wyniki analizy generowane są w języku **polskim**.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![Claude AI](https://img.shields.io/badge/Claude-AI-orange)

---

## ✨ Funkcje

### Diagnostyki sieciowe
| Check | Opis |
|---|---|
| **Ping** | ICMP – utrata pakietów, RTT min/avg/max |
| **DNS** | Wszystkie typy rekordów, spójność między resolverami (Google/Cloudflare/Quad9) |
| **HTTP/HTTPS** | Status kod, TTFB, nagłówki bezpieczeństwa, redirecty |
| **SSL/TLS** | Ważność certyfikatu, wersja TLS, cipher suite |
| **Porty TCP** | Skanowanie portów (80, 443, 8080 i inne) |
| **Traceroute** | Ścieżka routingu z geolokalizacją hopów |
| **Interfejsy** | Lokalne karty sieciowe, status, statystyki |

### Dashboard webowy
- **Przegląd** – kafelki statusu dla wszystkich monitorowanych celów
- **Live diagnostyka** – wyniki pojawiają się w czasie rzeczywistym (WebSocket)
- **AI Summary** – analiza Claude z streamingiem tokenów, po polsku
- **Mapa traceroute** – Leaflet.js z geolokalizacją hopów
- **Historia** – wszystkie diagnostyki w SQLite z wykresem Risk Score
- **Porównanie runów** – side-by-side diff dwóch diagnostyk
- **Eksport** – raport HTML (do druku/PDF) lub JSON
- **Alerty** – system alertów z potwierdzaniem
- **Dark/Light mode**

### AI (Claude API)
- Analiza wyłącznie po **polsku**
- **Streaming** tokenów – odpowiedź pojawia się na bieżąco
- **Kontekst historyczny** – AI widzi poprzednie runy i wykrywa regresje
- **Kategoria problemu** – DNS / routing / TLS / firewall / performance / application
- **Sugerowane komendy** – konkretne komendy CLI do skopiowania
- **Ocena ryzyka** – 0–100

### Bezpieczeństwo
- Logowanie (JWT, 7-dniowe sesje)
- Poświadczenia z `.env`
- Docker z `NET_RAW` dla ping/traceroute

---

## 🚀 Szybki start

### Wymagania
- Python 3.12+
- Docker + Docker Compose (opcjonalnie)
- Klucz API Anthropic ([console.anthropic.com](https://console.anthropic.com))

### 1. Konfiguracja

```bash
git clone https://github.com/AdamParciak97/DNS-CLI-Troubleshooter.git
cd DNS-CLI-Troubleshooter

cp .env.example .env
# Edytuj .env i uzupełnij ANTHROPIC_API_KEY oraz hasło
```

### 2a. Uruchomienie przez Docker (zalecane)

```bash
docker compose up -d

# Dashboard dostępny na http://localhost:8080
```

### 2b. Uruchomienie lokalne

```bash
pip install fastapi "uvicorn[standard]" anthropic sqlmodel dnspython \
    httpx psutil pydantic-settings python-dotenv apscheduler \
    rich typer websockets python-whois

python run_dashboard.py
# Dashboard dostępny na http://localhost:8080
```

---

## 🖥 CLI

```bash
# Szybka diagnostyka
python -m cli_troubleshooter.cli.app run google.com

# Pełna diagnostyka
python -m cli_troubleshooter.cli.app run google.com --profile full

# Konkretne checki
python -m cli_troubleshooter.cli.app run 8.8.8.8 --checks ping,dns,ssl

# Historia
python -m cli_troubleshooter.cli.app history
python -m cli_troubleshooter.cli.app history google.com --last 5

# Alerty
python -m cli_troubleshooter.cli.app alerts

# Uruchomienie dashboardu
python -m cli_troubleshooter.cli.app dashboard --port 8080
```

### Profile diagnostyczne

| Profil | Checki |
|---|---|
| `quick` | interfaces, dns, ping, http |
| `full` | interfaces, dns, ping, traceroute, ports, http, ssl |
| `web` | dns, ping, http, ssl, ports |
| `connectivity` | interfaces, dns, ping, traceroute |

---

## ⚙️ Konfiguracja `.env`

```env
# Wymagane
ANTHROPIC_API_KEY=sk-ant-api03-...

# Autentykacja dashboardu
CT_USERNAME=admin
CT_PASSWORD=twoje-haslo

# Klucz JWT (zmień na losowy ciąg)
CT_SECRET_KEY=losowy-ciag-minimum-32-znaki

# Opcjonalne
CT_DEFAULT_PROFILE=quick
CT_PORT=8080
CT_DATA_RETENTION_DAYS=90
```

---

## 🐳 Docker

```bash
# Uruchomienie
docker compose up -d

# Zatrzymanie
docker compose down

# Logi
docker compose logs -f

# Rebuild po zmianach kodu
docker compose up -d --build

# Wejście do kontenera
docker exec -it cli-troubleshooter bash
```

Dane (baza SQLite) są persystowane w katalogu `./data/` na hoście.

---

## 🏗 Struktura projektu

```
cli-troubleshooter/
├── cli_troubleshooter/
│   ├── config.py                    # Konfiguracja (Pydantic Settings)
│   ├── models.py                    # Modele ORM (SQLModel) + Pydantic
│   ├── auth.py                      # JWT autentykacja
│   ├── ai/
│   │   └── analyzer.py              # Integracja Claude API + fallback regułowy
│   ├── diagnostics/
│   │   ├── runner.py                # Orchestrator (asyncio)
│   │   └── checks/                  # ping, dns, http, ssl, ports, traceroute, interfaces
│   ├── storage/
│   │   ├── db.py                    # SQLite engine
│   │   └── repositories.py          # CRUD operacje
│   ├── cli/
│   │   └── app.py                   # CLI (Typer + Rich)
│   └── dashboard/
│       ├── app.py                   # FastAPI aplikacja
│       ├── routers/                 # REST API + WebSocket
│       └── static/
│           └── index.html           # SPA (Alpine.js + Chart.js + Leaflet.js)
├── run_dashboard.py                 # Skrypt startowy
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 📡 API

| Endpoint | Metoda | Opis |
|---|---|---|
| `POST /api/auth/login` | POST | Logowanie, zwraca JWT |
| `POST /api/diagnose` | POST | Uruchom diagnostykę (sync) |
| `GET /api/history` | GET | Lista historii |
| `GET /api/history/{id}` | GET | Szczegóły runu |
| `DELETE /api/history/{id}` | DELETE | Usuń run |
| `GET /api/alerts` | GET | Lista alertów |
| `PATCH /api/alerts/{id}/ack` | PATCH | Potwierdź alert |
| `GET /api/export/{id}/html` | GET | Eksport HTML |
| `GET /api/export/{id}/json` | GET | Eksport JSON |
| `WS /ws/diagnose` | WebSocket | Live diagnostyka ze streamingiem AI |

---

## 🛠 Technologie

| Warstwa | Technologia |
|---|---|
| CLI | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| Baza danych | SQLite via [SQLModel](https://sqlmodel.tiangolo.com/) |
| AI | [Anthropic Claude API](https://docs.anthropic.com/) |
| Frontend | [Alpine.js](https://alpinejs.dev/) + [Tailwind CSS](https://tailwindcss.com/) + [Chart.js](https://www.chartjs.org/) + [Leaflet.js](https://leafletjs.com/) |
| Konteneryzacja | Docker + Docker Compose |

---

## 📄 Licencja

MIT


## 📸 Screenshots
<img width="943" height="902" alt="image" src="https://github.com/user-attachments/assets/69ce17f5-c906-4ec4-8bdf-f7b20be40300" />

