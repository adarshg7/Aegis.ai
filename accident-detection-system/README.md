# 🚨 Advanced AI Accident Detection System

A **production-grade**, dual-phase accident detection and response platform powered by **RT-DETR + YOLOv9 ensemble AI**, **Apache Kafka**, **PostGIS**, and **TimescaleDB**.

---

## Architecture

```
CCTV / Dashcam Streams
        │
        ▼
 ┌──────────────────┐       ┌──────────────┐
 │  AI Engine       │──────▶│  Kafka       │
 │  RT-DETR+YOLOv9  │       │  accident.   │
 │  Ensemble        │       │  events      │
 └──────────────────┘       └──────┬───────┘
                                   │
                            ┌──────▼───────┐
                            │  FastAPI      │
                            │  Backend      │◀── External APIs
                            │  (Async)      │    (Mappls, News)
                            └──┬───────┬───┘
                   ┌───────────┘       └────────────┐
              ┌────▼────┐                      ┌────▼────┐
              │Postgres  │                      │  Redis  │
              │+PostGIS  │                      │Pub/Sub  │
              │+Timescale│                      │ Cache   │
              │+pgvector │                      └─────────┘
              └──────────┘
                   │ WebSocket
        ┌──────────┴──────────┐
   ┌────▼────┐          ┌─────▼────┐
   │Gov Dash │          │Driver PWA│
   │  React  │          │  React   │
   │  :3000  │          │  :3001   │
   └─────────┘          └──────────┘
```

---

## Quick Start

### 1. Copy and configure environment
```bash
cp .env.example .env
# Edit .env — set DB passwords, JWT secret, and API keys
```

### 2. Launch all services
```bash
docker-compose up --build -d
# First launch takes ~5 min (pulls images, builds containers)

# Watch logs
docker-compose logs -f backend
docker-compose logs -f ai-engine
```

### 3. Verify
```bash
# Backend health
curl http://localhost:8000/health

# Simulate an accident (needs auth token)
curl -X POST http://localhost:8000/api/v1/accidents/simulate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 28.6139, "longitude": 77.2090, "severity": "HIGH", "confidence_score": 0.92}'
```

### 4. Access URLs
| Service | URL |
|---|---|
| Government Dashboard | http://localhost:3000 |
| Driver PWA | http://localhost:3001 |
| Backend API Docs | http://localhost:8000/api/docs |
| Kafka UI (dev) | http://localhost:8080 |
| Prometheus Metrics | http://localhost:8000/metrics |

---

## Key Features

| Feature | Technology |
|---|---|
| AI Accident Detection | **RT-DETR + YOLOv9 weighted ensemble** (0.55/0.45) |
| Event Streaming | **Apache Kafka** (exactly-once, idempotent) |
| Geospatial Queries | **PostGIS** ST_DWithin radius searches |
| Time-Series Analytics | **TimescaleDB** hypertable auto-partitioning |
| AI Embeddings | **pgvector** for similarity search |
| Real-Time Push | **WebSockets** (multi-room, auto-reconnect) |
| Emergency Alerts | **Twilio** SMS + Voice Call |
| Driver Notifications | **Firebase FCM** push |
| Shop Alerts | **MSG91 WhatsApp** → SMS fallback |
| Map Data | **Mappls** (India) + Leaflet.js dark theme |
| External Data | Mappls Traffic API ingestion + deduplication |
| Auth | **JWT** (15-min access + 7-day refresh) + RBAC |
| Rate Limiting | Slowapi 60 req/min API, 5/min auth |
| Observability | **Prometheus** + structured JSON logs (structlog) |

---

## API Keys Required (in .env)
```
TWILIO_ACCOUNT_SID=...      # SMS + Voice calls to ambulance/police
TWILIO_AUTH_TOKEN=...
FIREBASE_SERVER_KEY=...     # Push to drivers
MAPPLS_API_KEY=...          # Maps + nearby shops (India)
GOOGLE_MAPS_API_KEY=...     # Fallback maps + places
MSG91_API_KEY=...           # WhatsApp to shops
```

> **DRY_RUN_NOTIFICATIONS=true** by default — no real SMS/calls are sent. All notifications are logged to DB. Set to `false` for production.

---

## Project Structure
```
accident-detection-system/
├── backend/                # FastAPI Python 3.11
│   └── app/
│       ├── api/            # auth, accidents, websocket routes
│       ├── core/           # config, security, DB, Redis, Kafka
│       ├── models/         # SQLAlchemy ORM (PostGIS + pgvector)
│       ├── schemas/        # Pydantic v2 validation
│       ├── services/       # accident, notification, geo, external data
│       └── websocket/      # multi-room WS manager
├── ai-engine/              # RT-DETR + YOLOv9 ensemble detector
│   ├── detector.py         # ensemble voting + debounce
│   ├── frame_buffer.py     # thread-safe ring buffer
│   └── stream_processor.py # multi-camera RTSP reader + Kafka publisher
├── frontend-gov/           # Government Dashboard (React + Vite)
│   └── src/pages/          # LoginPage, DashboardPage, IncidentsPage, AnalyticsPage
├── frontend-user/          # Driver PWA (React + Vite + Service Worker)
│   └── src/pages/          # LoginPage, MapPage, AlertsPage, SOSPage
├── nginx/                  # Reverse proxy (TLS, rate limit, WS upgrade)
├── infra/                  # DB init SQL (TimescaleDB hypertable)
├── docker-compose.yml      # 9 services with health checks
└── .env.example            # Configuration template
```

---

## Security Checklist
- [x] JWT with short-lived access tokens (15 min)
- [x] bcrypt password hashing
- [x] RBAC (GOVERNMENT / DRIVER / ADMIN roles)
- [x] Rate limiting on all endpoints
- [x] SQL injection prevention (ORM-only, parameterized queries)
- [x] Input validation (Pydantic v2 on all inputs)
- [x] HTTPS enforced (nginx TLS termination)
- [x] Security headers (X-Frame-Options, CSP, XSS protection)
- [x] Audit logging for all sensitive operations
- [x] Non-root Docker containers
- [x] Secrets in .env (never committed)
