# OmniFlow: Multi-Agent Retail Intelligence System

A unified retail assistant powered by isolated multi-agent orchestration. OmniFlow handles orders, shipments, payments, returns, refunds, NDRs, and exchanges with deterministic, database-grounded responses and natural conversational UI.

---

## 🚀 Features

- **Multi-Agent Architecture**: Isolated agents per domain (ShopCore, ShipStream, PayGuard, CareDesk) with separate SQLite databases.
- **Deterministic Tracking**: Immediate, grounded responses for shipment/order tracking without filler or delays.
- **Natural Conversational UI**: Chat, voice, and image capture with backend-generated responses only.
- **Return Photo Evidence**: Capture and store item photos for returns with unique ticket and reverse shipment IDs.
- **Purchase Flow**: Create unique order IDs and shipment tracking on purchase.
- **Voice Support**: Whisper-based transcription and TTS for spoken queries.
- **Docker Support**: Ready-to-deploy containerized setup.

---

## 📋 Prerequisites

- **Python 3.11+**
- **Git** (for cloning and version control)
- **Docker & Docker Compose** (optional, for containerized deployment)
- **OpenAI API key** (for LLM, Whisper, and TTS)

### Frameworks & Protocols Used

- **Backend Framework**: Django 4.x with Django REST Framework
- **Database**: SQLite (multi-database routing per agent)
- **Agent Orchestration**: LangChain + LangGraph
- **API Exposure**: All agents exposed via REST API endpoints
- **Protocol**: MCP (Model Context Protocol) for agent communication
- **LLM API**: OpenAI (GPT for reasoning, Whisper for transcription, TTS for speech)
- **Real-time Communication**: HTTP/REST API (WebSockets optional via Channels)
- **Containerization**: Docker with Docker Compose
- **Task Queue**: Redis (optional, for Channels/WebSockets)
- **ASGI Server**: Daphne (for Channels/WebSockets)
- **Environment Management**: python-dotenv
- **Image Processing**: Pillow (for return photo evidence)
- **Voice**: OpenAI Whisper (speech-to-text) and TTS (text-to-speech)
- **Web Server**: Django development server or Uvicorn/Gunicorn (production)

---

## 🛠️ Quick Start (Local Development)

### 1. Clone and Set Up

```bash
git clone <your-repo-url>
cd Multi-Agent-Orchestration-System-for-unifiled-retail-intelligence
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure Environment

Create a `.env` file in the root:

```env
OPENAI_API_KEY=sk-...
DEBUG=1
SECRET_KEY=your-secret-key-here
```

### 3. Initialize Databases & Seed Data

```bash
cd omniflow
python manage.py migrate
python manage.py load_dummy_shipments
python manage.py seed_users
python manage.py seed_payguard
```

### 4. Run the Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to use OmniFlow.

---

## 🐳 Docker Deployment

### Build & Run with Docker Compose

```bash
docker-compose up --build
```

- The app will be available at `http://localhost:8000`
- SQLite databases persist to `./omniflow/db` on the host
- Logs are available via `docker-compose logs -f`

### Production Notes

- Change `SECRET_KEY` in `docker-compose.yml`
- For production, consider using Gunicorn instead of Django’s runserver

---

## 🧩 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                 Frontend (omni_ui.html)            │
│  • Chat, voice, image capture                      │
│  • No assistant text generation (backend-only)     │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP POST /api/query/
                      ▼
┌─────────────────────────────────────────────────────┐
│           API Gateway (views.py)                    │
│  • Normalizes queries                               │
│  • Extracts tracking/order IDs                      │
│  • Routes to supervisor or deterministic paths      │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│         Supervisor Graph (supervisor_graph.py)      │
│  • Orchestrates agents                              │
│  • Synthesizes final response                      │
└─────────────┬───────────────┬───────────────┬───────┘
              │               │               │
              ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  ShopCore   │ │ ShipStream  │ │  PayGuard   │
│  (Orders)   │ │ (Shipments) │ │ (Payments)  │
└─────────────┘ └─────────────┘ └─────────────┘
              │               │               │
              ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  shopcore   │ │ shipstream  │ │  payguard   │
│   DB (SQLite)│ │   DB (SQLite)│ │   DB (SQLite)│
└─────────────┘ └─────────────┘ └─────────────┘
```

### Key Design Principles

- **Deterministic Tracking**: When a tracking ID is present, the system bypasses LLM inference and returns database-grounded facts immediately.
- **No Filler Phrases**: API-level sanitization removes “let me check” and similar delays.
- **Backend-Only Responses**: All assistant text, including the initial greeting, is generated by the backend.
- **Session Persistence**: Uses Django’s session framework to maintain conversation context.

---

## 📱 Usage Examples

### Tracking a Shipment

```
User: hello I need to track the shipment ID of FWD-1001 and tell me the current status and ETA
OmniFlow: FWD-1001 is currently In Transit. Estimated arrival is 2024-12-25.
```

### Starting a Return with Photo

```
User: I want to return my order
OmniFlow: Please provide your order ID or tracking number.
User: FWD-1001
OmniFlow: Please attach a photo of the item you’re returning.
[User uploads photo]
OmniFlow: Return created. Your return ticket ID is RT-7890 and reverse shipment ID is REV-4567.
```

### Wallet Balance

```
User: What’s my wallet balance?
OmniFlow: Your wallet balance is 125.50 USD.
```

---

## 🧪 Testing

### Run Tests

```bash
cd omniflow
python manage.py test
```

### Manual Testing Checklist

- [ ] Initial greeting appears on page load (backend-generated)
- [ ] Tracking queries with embedded IDs work immediately
- [ ] No “let me check” filler appears in tracking responses
- [ ] Return flow with photo evidence creates ticket and reverse shipment IDs
- [ ] Voice transcription and TTS work end-to-end
- [ ] Docker build and run succeed

---

## 📂 Project Structure

```
Multi-Agent-Orchestration-System-for-unifiled-retail-intelligence/
├── omniflow/
│   ├── api_gateway/          # API views and routing
│   ├── backend/              # Django settings & URLs
│   ├── caredesk/             # Returns & tickets
│   ├── payguard/             # Wallets & payments
│   ├── shipstream/           # Shipments & tracking
│   ├── shopcore/             # Orders & users
│   ├── core/orchestration/   # Supervisor graph
│   ├── utils/                # Prompts, logging, text2sql
│   ├── templates/            # UI (omni_ui.html)
│   └── db/                   # SQLite databases (one per app)
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── pyproject.toml
└── README.md
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM, Whisper, TTS | Required |
| `DEBUG` | Enable Django debug mode | `1` |
| `SECRET_KEY` | Django secret key | Randomly generated |

### Database Routing

Each sub-agent uses its own SQLite database via `omniflow/backend/db_router.py`. This ensures strict isolation and allows independent seeding per domain.

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

[Add your license here]

---

## 🆘 Troubleshooting

### Tracking ID Not Recognized

- Check the server logs for `[DEBUG]` lines to see if the ID is extracted
- Ensure the ID format matches: `FWD-1001`, `REV-1001`, `NDR-1001`, or `EXC-1001`

### Voice Not Working

- Verify `OPENAI_API_KEY` is set
- Check browser microphone permissions
- Ensure no other tab is using the microphone

### Docker Build Issues

- Ensure `requirements.txt` is up to date
- Check for syntax errors in `pyproject.toml`

---

## 📞 Support

For issues or questions, please open an issue on GitHub.