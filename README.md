# Aegis.ai

Aegis.ai is an AI-powered accident detection and emergency response platform designed to detect road accidents from video feeds, process AI-generated events, and provide real-time information through government and driver-facing interfaces.

The system combines AI-based detection, event streaming, backend processing, real-time communication, and dashboard interfaces into a unified road-safety platform.

The main application is located under:

```text
accident-detection-system/
```

## Features

- Real-time accident detection from video streams
- AI-powered accident analysis
- Kafka-based event streaming
- FastAPI backend for accident processing
- Government monitoring and analytics dashboard
- Driver-facing interface for alerts and actions
- Redis-backed processing and caching
- PostgreSQL/PostGIS database support
- WebSocket-based real-time updates
- JWT-based authentication
- Role-based access control
- API rate limiting
- Structured logging and validation
- Dockerized deployment
- Notification-ready architecture

## Tech Stack

### AI and Event Processing

- Python
- RT-DETR / YOLOv9-style detection workflow
- Kafka
- Stream processing modules

### Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- PostgreSQL/PostGIS
- Redis
- JWT authentication
- WebSockets
- Rate limiting

### Frontend

- React
- Vite
- React Router
- Recharts
- Leaflet
- Zustand
- Axios

### Infrastructure

- Docker
- Docker Compose
- NGINX
- PostgreSQL/PostGIS
- Redis
- Kafka

## Project Structure

```text
KodeMaster.ai/
├── accident-detection-system/
│   ├── ai-engine/
│   │   ├── detector.py
│   │   ├── frame_buffer.py
│   │   ├── stream_processor.py
│   │   └── Dockerfile
│   │
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   ├── websocket/
│   │   │   └── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── frontend-gov/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   │
│   ├── frontend-user/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   │
│   ├── infra/
│   │   └── init.sql
│   │
│   ├── nginx/
│   │   └── nginx.conf
│   │
│   ├── docker-compose.yml
│   ├── .env.example
│   └── README.md
│
├── .gitignore
└── README.md
```

## System Architecture

KodeMaster.ai follows an event-driven architecture in which video streams are processed by the AI detection engine and detected incidents are transmitted through Kafka to the backend.

The backend processes accident events and coordinates database storage, Redis services, and real-time communication with the frontend applications.

```text
┌──────────────────────┐
│   Camera / Video     │
│       Streams        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│     AI Engine        │
│                      │
│ Accident Detection   │
│ Frame Processing     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│        Kafka         │
│    Event Streaming   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    FastAPI Backend   │
│                      │
│ Accident Processing  │
│ Authentication       │
│ Business Logic       │
│ REST APIs            │
└───────┬──────┬───────┘
        │      │
        │      └─────────────────┐
        ▼                        ▼
┌───────────────┐       ┌────────────────┐
│  PostgreSQL   │       │     Redis      │
│   / PostGIS   │       │                │
│               │       │ Cache / Events │
│ Accident Data │       │                │
│ Location Data │       └────────────────┘
└───────────────┘
        │
        ▼
┌──────────────────────┐
│   WebSocket Layer    │
│   Real-time Updates  │
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌───────────┐ ┌──────────────┐
│Government │ │    Driver    │
│ Dashboard │ │   Frontend   │
└───────────┘ └──────────────┘
```

## Workflow

The main accident detection workflow is:

```text
Camera / Video Stream
        ↓
AI Detection Engine
        ↓
Accident Detection
        ↓
Kafka Event Stream
        ↓
FastAPI Backend
        ↓
Accident Processing
        ↓
PostgreSQL + Redis
        ↓
WebSocket Updates
        ↓
Government Dashboard + Driver Interface
```

This allows accident events to move from detection to backend processing and finally to user-facing interfaces in near real time.

## Prerequisites

Before running KodeMaster.ai, make sure the following are installed:

- Docker
- Docker Compose
- Python 3.11 or higher
- Node.js 18 or higher
- npm
- Git

## Environment Setup

Navigate to the main application directory:

```bash
cd accident-detection-system
```

Create the environment file:

```bash
cp .env.example .env
```

For Windows PowerShell, you can use:

```powershell
Copy-Item .env.example .env
```

Update the `.env` file with the required configuration.

Important configuration areas may include:

- Database credentials
- JWT secret
- Redis endpoint
- Kafka endpoint
- Twilio credentials
- Firebase credentials
- Map API keys
- Notification settings

Do not commit the actual `.env` file containing secrets to the repository.

## Running with Docker Compose

Docker Compose is the recommended way to run the complete system.

Navigate to the application directory:

```bash
cd accident-detection-system
```

Build and start the services:

```bash
docker compose up --build -d
```

To view running containers:

```bash
docker compose ps
```

To view service logs:

```bash
docker compose logs -f
```

To stop the application:

```bash
docker compose down
```

## Service Access

After the services have started successfully, the expected local endpoints are:

| Service | URL |
|---|---|
| Government Dashboard | `http://localhost:3000` |
| Driver Frontend | `http://localhost:3001` |
| Backend API | `http://localhost:8000` |
| Backend API Docs | `http://localhost:8000/api/docs` |
| Health Check | `http://localhost:8000/health` |

The exact ports may depend on the Docker Compose configuration.

## Health Check

The backend exposes a health endpoint for checking the operational status of the application.

```http
GET /health
```

You can test the endpoint using:

```bash
curl http://localhost:8000/health
```

A successful response indicates that the backend is running and available.

## Accident Simulation

The backend provides APIs for accident processing and simulation workflows.

A typical accident simulation request can be made using:

```bash
curl -X POST http://localhost:8000/api/v1/accidents/simulate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 28.6139,
    "longitude": 77.2090,
    "severity": "HIGH",
    "confidence_score": 0.92
  }'
```

The request contains information such as:

- Accident location
- Accident severity
- AI confidence score
- Authentication token

The exact request format depends on the backend API implementation.

## Government Dashboard

The government-facing frontend provides a centralized interface for monitoring detected accidents and analyzing incident information.

Potential dashboard capabilities include:

- Accident monitoring
- Incident location visualization
- Accident severity information
- Historical accident information
- Real-time event updates
- Operational monitoring
- Map-based visualization

## Driver Interface

The driver-facing frontend is designed to provide users with accident-related alerts and relevant information.

It can be used to support:

- Real-time accident notifications
- Incident information
- Location-based alerts
- User actions
- Emergency-response workflows

## Security

The platform includes several security-oriented components:

- JWT authentication
- Role-based access control
- API rate limiting
- Request validation
- Environment-based configuration
- Structured logging
- Protected administrative operations

### Production Security Recommendations

For production deployment:

- Store secrets in a secure secret-management system.
- Never expose `.env` files publicly.
- Use HTTPS/TLS for all external communication.
- Secure Kafka connections and credentials.
- Restrict database access.
- Protect administrative endpoints.
- Configure NGINX with appropriate security headers.
- Use strong JWT secrets.
- Apply appropriate network restrictions to Redis and PostgreSQL.

## Real-Time Communication

KodeMaster.ai uses WebSockets to provide real-time communication between the backend and frontend applications.

The general flow is:

```text
Accident Detected
       ↓
Backend Receives Event
       ↓
Event Processed
       ↓
WebSocket Notification
       ↓
Government Dashboard
       +
Driver Interface
```

This allows important accident information to be delivered without requiring the frontend to continuously poll the backend.

## Database and Storage

The platform uses PostgreSQL for persistent application data and supports PostgreSQL/PostGIS for location-aware data.

The database can store information related to:

- Accident events
- Locations
- Users
- Roles
- Incident information
- Operational data

Redis is used for fast-access data and backend processing requirements.

## Development

For development purposes, the main components can also be worked on independently:

```text
AI Engine
    ↓
Backend
    ↓
Government Frontend
    ↓
Driver Frontend
```

Each component contains its own configuration and dependencies where applicable.

## API Documentation

When the backend is running, API documentation is available through the configured FastAPI documentation endpoint:

```text
http://localhost:8000/api/docs
```

This can be used to inspect available API endpoints and test requests during development.

## Future Improvements

Potential future enhancements include:

- Improved accident detection accuracy
- Multi-camera accident detection
- Automatic emergency-service notifications
- Advanced accident severity classification
- Historical accident analytics
- Predictive accident-risk analysis
- Improved geospatial analytics
- Mobile application support
- Integration with emergency services
- Advanced notification channels
- AI-based incident summarization

## Summary

Aegis.ai is an AI-powered road-safety and emergency-response platform that combines computer vision, event-driven architecture, real-time communication, and web-based dashboards.

The platform connects an AI accident detection engine with Kafka-based event streaming, a FastAPI backend, PostgreSQL/PostGIS, Redis, WebSockets, and dedicated government and driver interfaces.

Its architecture is designed to support real-time accident detection, incident processing, monitoring, and notification workflows through a centralized platform.
