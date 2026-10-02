# SmartFarm AI

## Project Overview
SmartFarm AI is a full-stack agricultural decision-support application that helps farmers make practical day-to-day farming decisions using real farm data, real weather data, agricultural rules, and an AI assistant. It provides recommendations for irrigation, crop selection, and daily action plans to ensure optimal farm management.

## Problem Statement
Farmers face difficulties keeping track of rapidly changing weather patterns, accurate crop cycle needs, and timely interventions. Standard weather apps lack agricultural context, and generalized AI chatbots lack farm-specific real-time data integration, leading to suboptimal decision-making and reduced yields.

## Objectives
- Tell the farmer what to grow and when to grow it.
- Determine exactly when to irrigate based on weather forecasts and crop stages.
- Provide a clear, actionable daily and weekly farm plan.
- Serve as a smart, context-aware agricultural assistant (FarmAI) using Groq tool calling and Agricultural RAG.

## Features
- **Farmer & Farm Profile:** Manage multiple farms, fields, and soil profiles.
- **Crop Management & Calendars:** Track active crops, growth stages, and harvest windows.
- **Smart Irrigation Engine:** Rule-based irrigation scheduling factoring in rainfall, humidity, and temperature.
- **Risk Engine:** Real-time risk detection for weather anomalies and potential crop diseases.
- **Farm Action Plan:** Daily and 7-day task recommendations.
- **Groq FarmAI:** A specialized chat assistant executing actual tools to answer farm-specific questions.
- **Agricultural RAG:** Knowledge retrieval for crop guides and standard agricultural documents.
- **Telegram Integration:** Daily reminders, risk alerts, and direct interaction with FarmAI through Telegram.
- **Mandi Prices:** Integration to fetch market crop prices.

## Architecture
The application follows a clean monolithic architecture:
- **Frontend:** Vanilla HTML, CSS, JavaScript (No frontend framework). Responsive, modern, and lightweight.
- **Backend:** Python + FastAPI for robust asynchronous API endpoints.
- **Database:** PostgreSQL (currently configured with SQLite for local development, adaptable via environment variables), accessed via SQLAlchemy and managed by Alembic.
- **AI & Integrations:** Groq for LLM, OpenWeatherMap for weather data, Telegram Bot API for notifications. Background tasks are scheduled with APScheduler.

## Technology Stack
- **Frontend:** HTML5, CSS3, Vanilla JS, Chart.js
- **Backend:** Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic
- **Database:** PostgreSQL (SQLAlchemy compatible)
- **AI/LLM:** Groq API (Llama 3 / Mixtral models)
- **Background Tasks:** APScheduler
- **External Integrations:** OpenWeatherMap API, Telegram Bot API

## Project Structure
```
smartfarm-ai/
│
├── frontend/             # HTML/CSS/JS frontend files
├── backend/              # FastAPI application
│   ├── api/routes/       # API route definitions
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas for request/response validation
│   ├── services/         # Core services (Weather, AI, Telegram, Market)
│   ├── tools/            # Tools exposed to the Groq AI agent
│   ├── agents/           # LLM agent logic
│   ├── agriculture/      # Rule-based calculation engines (Irrigation, Risks, Calendar)
│   ├── notifications/    # Alert dispatching
│   ├── scheduler/        # APScheduler configuration
│   ├── rag/              # Retrieval-Augmented Generation logic
│   ├── database/         # DB connection and setup
│   ├── config/           # Environment and app settings
│   └── tests/            # Pytest test suite
├── data/                 # Seed data (crops, soil profiles)
├── alembic/              # Database migration scripts
├── .env                  # Environment variables
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd smartfarm-ai
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables
Create a `.env` file in the root directory (you can copy `.env.example`).
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/smartfarm

# APIs
GROQ_API_KEY=your_groq_api_key
WEATHER_API_KEY=your_openweathermap_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# App Config
APP_ENV=development
APP_SECRET_KEY=your_secret_key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:5500,null
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
LOG_LEVEL=INFO
```

## Database Setup
1. **Configure PostgreSQL:** Ensure PostgreSQL is running and your `DATABASE_URL` is set correctly. (SQLite is supported out-of-the-box for local testing).
2. **Apply Migrations:**
   ```bash
   alembic upgrade head
   ```

## Weather API Setup
- Sign up at [OpenWeatherMap](https://openweathermap.org/) and obtain an API key.
- Add it as `WEATHER_API_KEY` in your `.env`.

## Groq Setup
- Sign up at [Groq Console](https://console.groq.com/) and create an API key.
- Add it as `GROQ_API_KEY` in your `.env`.

## Telegram Setup
- Message `@BotFather` on Telegram to create a new bot.
- Copy the provided HTTP API token and set `TELEGRAM_BOT_TOKEN` in your `.env`.

## Running Locally
Start the FastAPI server (which also serves the frontend and starts the background scheduler):
```bash
python backend/main.py
```
Alternatively, using `uvicorn`:
```bash
uvicorn backend.main:app --reload --port 8000
```
Open `http://localhost:8000/` in your browser to access the frontend dashboard.
Open `http://localhost:8000/docs` to view the Swagger API documentation.

## Testing
Run the comprehensive test suite with `pytest`:
```bash
pytest backend/tests/ -v
```

## API Documentation
The API documentation is automatically generated by FastAPI.
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Agricultural Assumptions and Models
- **Irrigation Calculation:** Estimated requirement is purely rule-based. It compares crop growth stage water demands with expected rainfall. If expected rainfall exceeds crop demand, irrigation is postponed.
- **Crop Risk Detection:** Uses hard thresholds for temperature, wind, and humidity. It serves as an alert system, not a definitive disease diagnosis. (e.g. High humidity + heavy rain = Potential Fungal Risk).
- **Crop Recommendations:** Suitable crops are filtered by matching current season, soil type, and location temperature against static crop reference data (found in `data/crops/crops.json`).

## Data Sources
- **Weather Data:** OpenWeatherMap API (live and forecasted).
- **Crop Catalog:** Internal JSON dataset (`data/crops/crops.json`), sourced from standard Indian agricultural guidelines.
- **Mandi Prices:** Mock integration currently; designed to connect to e-NAM APIs when available.

## Known Limitations
- **Weather API:** Relies entirely on third-party uptime and location accuracy. Micro-climates at the exact farm location might not be precisely captured.
- **AI Limitations:** The Groq FarmAI agent strictly relies on the tools provided. It cannot invent data, but complex logic errors might occur if conflicting tools return overlapping contexts.
- **Risk Prediction:** Disease prediction is purely environmental and does not incorporate leaf-image analysis or actual soil sampling.
- **Production Infrastructure:** The current setup relies on APScheduler running inside the web server process. For horizontal scaling in production, tools like Celery and Redis will be required.

## Future Improvements
- Leaf image disease detection.
- Satellite imagery integration for field health.
- Real-time IoT soil-moisture sensor integration.
- ML-based predictive irrigation rather than static rules.
- Multilingual voice assistant and WhatsApp integration.
