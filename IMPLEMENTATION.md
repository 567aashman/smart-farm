# SmartFarm — Implementation Plan

## 1. Project Overview

Build **SmartFarm**, a full-stack agricultural decision-support application that helps farmers make practical day-to-day farming decisions using:

- Farm and location information
- Soil information
- Crop information
- Live weather and forecasts
- Crop calendars
- Smart irrigation recommendations
- Crop suitability analysis
- Weather and crop risk analysis
- Daily and weekly farm action plans
- Mandi/market information
- Groq-powered AI agricultural assistant
- AI tool calling
- Agricultural RAG
- Telegram notifications and reminders
- Telegram-based AI assistant

The application must not be just a weather app or chatbot.

The core idea is:

> **Tell the farmer what to grow, when to grow it, when to irrigate it, what to do today, what risks to watch for, and answer farm-related questions using real farm and weather data.**

---

# 2. Development Philosophy

Build the system incrementally.

```text
PLAN
  ↓
IMPLEMENT
  ↓
TEST
  ↓
VERIFY
  ↓
FIX
  ↓
DOCUMENT
  ↓
NEXT PHASE
```

### Critical rule

**Implement and validate one phase completely before starting the next phase.**

Do not replace real production functionality with fake functionality simply to make the application appear complete.

Mocks may be used inside automated tests only.

---

# 3. Technology Stack

## Frontend

Keep the frontend simple and suitable for a first-year project:

- HTML5
- CSS3
- Vanilla JavaScript
- Fetch API
- Chart.js only where charts are genuinely required

### Do NOT use:

- React
- TypeScript
- Vite
- Next.js
- Tailwind
- React Router
- Redux
- Other frontend frameworks

The frontend should be understandable to a first-year student and easy to explain during a faculty/project viva.

---

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

---

## Database

- PostgreSQL

---

## AI

- Groq API
- Groq tool/function calling
- RAG architecture

---

## Weather

Use a real weather API providing:

- Current temperature
- Humidity
- Rainfall
- Rain probability
- Weather forecast
- Wind
- Sunrise/sunset

Keep the weather API behind a `WeatherService` so the provider can be changed later.

---

## Notifications

- Telegram Bot API
- APScheduler for scheduled reminders

Do not introduce Celery, Redis, Docker or other distributed infrastructure.

---

## Deployment

For this version, **do not use Docker**.

The project should run directly using:

```bash
python
uvicorn
PostgreSQL
```

and a normal browser for the frontend.

---

# 4. Target Architecture

```text
                         SmartFarm
                              │
                ┌─────────────┴─────────────┐
                │                           │
        HTML + CSS + JS                 FastAPI
          Frontend                      Backend
                │                           │
                │             ┌─────────────┼──────────────┐
                │             │             │              │
                │         PostgreSQL    Weather API     Groq API
                │             │             │              │
                │             │             │         FarmAI Agent
                │             │             │              │
                │             │             │        Tool Calling
                │             │             │              │
                │             │             │     ┌────────┼────────┐
                │             │             │     │        │        │
                │             │             │ Weather    Farm    Agriculture
                │             │             │ Tool       Tool      Tools
                │             │             │
                │             └─────────────┼──────────────┐
                │                           │              │
                │                       Scheduler       Telegram
                │                           │           Bot API
                │                           │              │
                └───────────────────────────┴──────────────┘
```

---

# 5. Repository Structure

Use a simple structure:

```text
smartfarm-ai/
│
├── frontend/
│   ├── index.html
│   ├── onboarding.html
│   ├── dashboard.html
│   ├── crops.html
│   ├── irrigation.html
│   ├── farm-ai.html
│   ├── styles/
│   │   └── style.css
│   ├── js/
│   │   ├── api.js
│   │   ├── dashboard.js
│   │   ├── onboarding.js
│   │   ├── crops.js
│   │   ├── irrigation.js
│   │   └── farm-ai.js
│   └── assets/
│
├── backend/
│   ├── main.py
│   ├── api/
│   │   └── routes/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── tools/
│   ├── agents/
│   ├── agriculture/
│   ├── notifications/
│   ├── scheduler/
│   ├── rag/
│   ├── database/
│   ├── config/
│   └── tests/
│
├── data/
│   ├── crops/
│   ├── soil/
│   ├── disease/
│   └── agriculture/
│
├── docs/
│
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── IMPLEMENTATION.md
```

---

# 6. Environment Variables

Create:

```text
.env
```

Never hard-code API credentials.

Required:

```text
DATABASE_URL=

GROQ_API_KEY=

WEATHER_API_KEY=

TELEGRAM_BOT_TOKEN=
```

Create:

```text
.env.example
```

with variable names only.

---

# PHASE 0 — Project Foundation

## Goal

Create a simple full-stack project that runs locally.

### Backend

Create:

- FastAPI application
- PostgreSQL connection
- SQLAlchemy
- Alembic
- Environment configuration
- CORS
- Logging
- Health endpoint

Endpoint:

```text
GET /health
```

Expected:

```json
{
  "status": "ok"
}
```

### Frontend

Create basic:

```text
index.html
style.css
app.js
```

Create a simple landing page and verify that JavaScript can communicate with FastAPI.

### Validation

Verify:

```text
Backend starts
PostgreSQL connects
/health returns 200
Frontend opens in browser
Frontend successfully calls backend
```

Do not proceed until this works.

---

# PHASE 1 — Database and Farm Model

Create:

```text
User
Farm
Field
SoilProfile
Crop
CropStage
IrrigationRecord
FarmTask
WeatherRecord
Notification
```

Relationship:

```text
User
 └── Farm
      ├── SoilProfile
      ├── Field
      │    └── Crop
      │         └── CropStage
      ├── IrrigationRecord
      ├── FarmTask
      └── Notification
```

Initially support:

- Wheat
- Rice
- Maize
- Mustard
- Potato
- Tomato
- Cotton
- Sugarcane

Store:

```text
crop_name
season
temperature_min
temperature_max
rainfall_requirement
water_requirement
soil_preferences
sowing_window
growth_duration
growth_stages
```

Keep crop information configurable.

### Validation

Test:

- User creation
- Farm creation
- Soil profile
- Field creation
- Crop creation
- Crop retrieval

---

# PHASE 2 — Farmer Onboarding

Create simple HTML forms.

Farmer enters:

```text
Name
Location
Farm area
Soil type
Soil pH
Irrigation method
Water source
```

Then:

```text
Crop
Field
Area
Sowing date
```

Pages:

```text
/onboarding
/farm
/crops
```

Use JavaScript `fetch()` to communicate with FastAPI.

---

# PHASE 3 — Weather Integration

Create:

```text
WeatherService
```

Methods:

```python
get_current_weather(location)
get_forecast(location, days)
get_rainfall_forecast(location, days)
get_humidity(location, days)
get_wind(location, days)
```

Dashboard displays:

```text
Temperature
Humidity
Rain probability
Rainfall
Wind
7-day forecast
Sunrise
Sunset
```

Handle:

- Invalid location
- API failure
- Missing API key
- Timeout

Never fabricate missing weather data.

---

# PHASE 4 — Smart Irrigation Engine

Create:

```text
IrrigationEngine
```

Inputs:

```text
Crop
Crop stage
Field area
Soil type
Weather
Rain forecast
Temperature
Humidity
```

Output:

```json
{
  "irrigation_required": true,
  "recommended_date": "...",
  "recommended_time": "06:00",
  "estimated_requirement_mm": 18,
  "reason": "...",
  "confidence": "medium"
}
```

Start with transparent rule-based agricultural logic.

Example:

```text
High expected rainfall
        ↓
Postpone irrigation

Low rainfall
+
High crop water demand
        ↓
Recommend irrigation
```

The LLM must NOT calculate irrigation values.

The agricultural engine does the calculation.

FarmAI only explains the result.

---

# PHASE 5 — Crop Recommendation

Create:

```text
CropRecommendationEngine
```

Inputs:

```text
Location
Season
Temperature
Rainfall
Soil
Water availability
```

Output:

```text
Wheat
Suitable

Mustard
Suitable

Potato
Moderate

Rice
Not suitable
```

Every recommendation must have an explanation.

---

# PHASE 6 — Crop Calendar

Track:

```text
Land Preparation
       ↓
Sowing
       ↓
Germination
       ↓
Vegetative Growth
       ↓
Flowering
       ↓
Maturity
       ↓
Harvest
```

Create:

```text
CropCalendarService
```

Generate farm tasks based on:

- Crop
- Sowing date
- Current stage
- Expected stage duration

---

# PHASE 7 — Risk Engine

Create:

```text
RiskEngine
```

Detect:

### Weather

```text
Heavy Rain
Heat Stress
High Wind
Dry Spell
```

### Crop/environment

```text
High Humidity
Excess Moisture
Low Temperature
Potential Fungal Risk
```

Do not claim a disease diagnosis from weather alone.

Use:

```text
Potential risk
Conditions are favorable for...
Inspect the crop...
```

---

# PHASE 8 — Daily and 7-Day Farm Action Plan

Create:

```text
ActionPlanEngine
```

Combine:

```text
Crop Calendar
+
Irrigation Engine
+
Weather
+
Risk Engine
+
Farm Tasks
```

Output:

```text
TODAY

🌱 Inspect wheat
⚠️ Monitor humidity
💧 No irrigation required

TOMORROW

💧 Irrigate potato
6–8 AM

DAY 3

🌧️ Rain expected
Skip irrigation
```

This should be the primary dashboard section.

---

# PHASE 9 — Main Dashboard

Create using only:

```text
HTML
CSS
JavaScript
```

Dashboard sections:

```text
Header

Weather Summary

Today's Farm Actions

7-Day Weather Forecast

My Crops

Irrigation Recommendation

Risk Alerts

Crop Recommendations

Farm Analytics

Ask FarmAI
```

Make it responsive and mobile-friendly.

Do not use a frontend framework.

---

# PHASE 10 — Groq FarmAI

Use Groq API.

Architecture:

```text
User Question
      ↓
Groq
      ↓
Tool Selection
      ↓
Tool Execution
      ↓
Tool Result
      ↓
Groq
      ↓
Final Answer
```

Implement tools:

```text
get_farm_profile()
get_active_crops()
get_crop_stage()
get_current_weather()
get_weather_forecast()
calculate_irrigation()
get_crop_recommendations()
get_crop_calendar()
get_risk_analysis()
get_action_plan()
get_mandi_prices()
```

Example:

```text
User:
Should I irrigate my wheat tomorrow?

FarmAI
 ↓
get_active_crops()
 ↓
get_crop_stage()
 ↓
get_weather_forecast()
 ↓
calculate_irrigation()
 ↓
Groq
 ↓
Answer
```

The AI must never invent:

- Weather
- Farm data
- Irrigation values
- Crop requirements
- Mandi prices

---

# PHASE 11 — FarmAI Chat UI

Create:

```text
farm-ai.html
farm-ai.js
```

Simple chat interface:

```text
────────────────────────────
🤖 FarmAI
────────────────────────────

User:
Should I water my wheat tomorrow?

FarmAI:
Let me check your crop and weather...

FarmAI:
No irrigation is recommended tomorrow
because rainfall is expected.

────────────────────────────
Ask FarmAI...
[________________________]
```

Do not expose hidden chain-of-thought or internal reasoning.

---

# PHASE 12 — Agricultural RAG

Add agricultural knowledge retrieval.

Possible knowledge:

```text
Crop guides
Government agriculture documents
Disease information
Soil information
Fertilizer guidelines
Irrigation guidelines
```

Architecture:

```text
Question
   ↓
Retriever
   ↓
Relevant Documents
   ↓
Groq
   ↓
Answer
```

Use:

```text
Tools = live/dynamic information

RAG = agricultural knowledge
```

Examples:

```text
Weather → Tool
Farm data → Tool
Mandi price → Tool
Crop cultivation guide → RAG
```

---

# PHASE 13 — Telegram Integration

Create Telegram bot integration.

Flow:

```text
Farmer
   ↓
Telegram
   ↓
Start Bot
   ↓
Generate / enter linking code
   ↓
Connect account
   ↓
Store chat_id
```

Store:

```text
telegram_chat_id
telegram_connected
```

Never expose the bot token.

---

# PHASE 14 — Telegram Reminders

Use APScheduler.

Scheduler checks:

```text
FarmTask
IrrigationRecommendation
WeatherAlerts
RiskAlerts
CropCalendar
```

Then sends Telegram messages.

Example:

```text
🌾 SMARTFARM REMINDER

Your wheat field may require irrigation.

Recommended time:
Tomorrow 6:00–8:00 AM

Expected rainfall:
2 mm

Estimated irrigation:
18 mm
```

Weather alert:

```text
🌧️ WEATHER ALERT

Heavy rainfall is expected tomorrow.

Recommended action:
Postpone irrigation.
```

Crop reminder:

```text
🌱 CROP REMINDER

Your wheat is entering the next growth stage.

Today's recommended action:
Inspect crop growth.
```

Prevent duplicate notifications.

---

# PHASE 15 — Telegram FarmAI

Allow users to ask FarmAI directly through Telegram.

```text
Telegram
   ↓
FastAPI
   ↓
FarmAI
   ↓
Tool Calling
   ↓
Groq
   ↓
Telegram Response
```

Example:

```text
Farmer:
Should I irrigate my wheat tomorrow?

Bot:
🌾 I checked your wheat and tomorrow's
weather.

Irrigation is not recommended tomorrow
because rainfall is expected.
```

---

# PHASE 16 — Mandi / Market Information

Create:

```text
MarketService
```

Function:

```text
get_mandi_prices(crop, location)
```

Display:

```text
Wheat
₹XXXX / quintal

Mustard
₹XXXX / quintal

Potato
₹XXXX / quintal
```

Never fabricate market prices.

If live data is unavailable, clearly show that the data is unavailable or show the source/date of the available data.

---

# PHASE 17 — Farm Analytics

Display:

```text
Active Crops
Irrigation Events
Estimated Water Requirement
Rainfall
Upcoming Tasks
Risk Events
```

Example:

```text
WEEKLY FARM SUMMARY

Water Requirement
████████████

Rainfall
██████

Irrigation Events
3

Upcoming Tasks
7

Active Risks
2
```

Any estimated metric must be clearly labelled as estimated.

---

# PHASE 18 — Notification Preferences

Allow farmers to enable/disable:

```text
Irrigation reminders
Weather alerts
Crop reminders
Risk alerts
Daily farm summary
```

Allow preferred notification time.

Avoid notification spam.

Deduplicate repeated alerts.

---

# PHASE 19 — Security and Reliability

Never expose:

```text
GROQ_API_KEY
WEATHER_API_KEY
TELEGRAM_BOT_TOKEN
```

to frontend JavaScript.

Validate:

```text
Farm area
Soil values
Crop
Dates
Location
User input
```

If Weather API fails:

```text
Weather temporarily unavailable.
```

If Groq fails:

```text
FarmAI is temporarily unavailable.
```

The rest of the application should continue working.

Log:

```text
API errors
Scheduler events
Telegram notifications
AI tool calls
Agricultural-engine decisions
```

---

# PHASE 20 — Testing

Every major module requires automated tests.

Test:

```text
Database
API endpoints
Agricultural engines
Weather service
Telegram service
AI tools
Scheduler
```

Agricultural test cases:

```text
High rainfall → irrigation postponed

Low rainfall + high demand → irrigation recommended

Suitable soil + correct season → crop recommended

Wrong season → crop suitability reduced/rejected

High humidity + rainfall → fungal risk warning
```

AI tests:

```text
Should I irrigate my wheat tomorrow?
What should I grow this season?
What is my farm status?
What should I do today?
Is there any weather risk?
When should I sow wheat?
What is the current mandi price?
```

Verify:

1. Correct tool selected.
2. Correct tool arguments.
3. Correct tool result.
4. Final response uses tool result.
5. No fabricated information.

---

# PHASE 21 — End-to-End Validation

Test the complete workflow:

```text
Create Farmer
     ↓
Create Farm
     ↓
Add Soil
     ↓
Add Wheat
     ↓
Add Sowing Date
     ↓
Fetch Weather
     ↓
Calculate Irrigation
     ↓
Generate Farm Tasks
     ↓
Generate 7-Day Plan
     ↓
Ask FarmAI
     ↓
Verify Tool Calling
     ↓
Connect Telegram
     ↓
Trigger Reminder
     ↓
Receive Telegram Message
     ↓
Ask FarmAI Through Telegram
     ↓
Receive Answer
```

This complete workflow must work before declaring the project finished.

---

# PHASE 22 — Documentation

Create `README.md` containing:

```text
Project Overview
Problem Statement
Objectives
Features
Architecture
Technology Stack
Project Structure
Installation
Environment Variables
Database Setup
Weather API Setup
Groq Setup
Telegram Setup
Running Locally
Testing
API Documentation
Known Limitations
Future Improvements
```

Also document:

```text
Agricultural calculation assumptions
Data sources
Weather API limitations
AI limitations
Risk prediction limitations
```

---

# FINAL FEATURE CHECKLIST

The completed application must contain:

- [ ] Farmer onboarding
- [ ] Farm profile
- [ ] Field management
- [ ] Soil profile
- [ ] Crop management
- [ ] Crop recommendation
- [ ] Crop calendar
- [ ] Crop stage tracking
- [ ] Live weather
- [ ] 7-day weather forecast
- [ ] Smart irrigation
- [ ] Weather risk detection
- [ ] Crop/environment risk detection
- [ ] Disease-risk indication
- [ ] Daily action plan
- [ ] 7-day action plan
- [ ] Farm dashboard
- [ ] Farm analytics
- [ ] Groq FarmAI
- [ ] Tool calling
- [ ] Agricultural RAG
- [ ] Telegram account linking
- [ ] Telegram irrigation reminders
- [ ] Telegram weather alerts
- [ ] Telegram crop reminders
- [ ] Telegram risk alerts
- [ ] Telegram FarmAI
- [ ] Mandi/market information
- [ ] Notification preferences
- [ ] Error handling
- [ ] Automated tests
- [ ] End-to-end tests
- [ ] Documentation

**Do NOT include Docker.**

**Do NOT use React or any frontend framework.**

**Frontend must use HTML + CSS + Vanilla JavaScript.**

---

# FUTURE ENHANCEMENTS

Do not implement these until the core application works:

```text
Leaf image disease detection
Satellite imagery
IoT soil-moisture sensors
Real soil-moisture integration
Yield prediction
Fertilizer optimization
ML-based irrigation prediction
Voice assistant
Regional-language support
WhatsApp integration
Mobile application
```

---

# PRODUCT PRINCIPLE

SmartFarm should follow:

```text
REAL FARM DATA
      +
REAL WEATHER DATA
      +
AGRICULTURAL RULES / MODELS
      +
AGRICULTURAL KNOWLEDGE
      ↓
RECOMMENDATION
      ↓
AI EXPLANATION
      ↓
FARMER ACTION
```

The LLM is an **assistant and orchestrator**, not the source of truth for agricultural calculations.

---

# ANTIGRAVITY EXECUTION INSTRUCTIONS

When implementing:

1. Read this entire `IMPLEMENTATION.md` before modifying the repository.
2. Inspect the existing repository first.
3. Do not overwrite working functionality without checking it.
4. Implement **one phase at a time**.
5. After each phase:
   - Run automated tests.
   - Start the backend.
   - Open/test the frontend.
   - Test relevant API endpoints.
   - Verify the user flow.
   - Fix all discovered errors.
6. Do not proceed if the current phase is failing.
7. Keep production logic separate from test mocks.
8. Never hard-code API keys.
9. Never fabricate weather, agricultural, or market information.
10. Keep agricultural calculations separate from LLM logic.
11. Keep external APIs behind service abstractions.
12. Keep the code simple enough for a first-year project.
13. Prefer understandable Python, HTML, CSS and JavaScript over unnecessary abstractions.
14. Do not introduce frameworks unless explicitly required by this document.
15. Do not introduce Docker.
16. Do not introduce React.
17. Maintain logs for important operations.
18. Update documentation when architecture changes.
19. At the end of every phase report:
    - What was implemented
    - Files changed
    - Tests executed
    - Test results
    - Known issues
    - Next phase
20. Never claim a feature is complete without testing it.
21. Use real integrations when credentials are available.
22. If credentials are unavailable, create the proper integration interface and clearly document the required configuration.

---

# DEFINITION OF DONE

The project is complete when a farmer can:

```text
Create Farm
     ↓
Add Soil Information
     ↓
Add Crop
     ↓
Fetch Weather
     ↓
Receive Irrigation Recommendation
     ↓
See Crop Calendar
     ↓
See Today's Farm Actions
     ↓
Receive Weather/Risk Alert
     ↓
Connect Telegram
     ↓
Receive Telegram Reminder
     ↓
Ask FarmAI
     ↓
FarmAI Uses Tools
     ↓
Receive Data-Based Answer
     ↓
Ask FarmAI From Telegram
     ↓
Receive Answer
```

The final application should feel like:

> **A personal digital farming assistant that watches farm conditions, weather and crop stages and tells the farmer what action to take next.**
