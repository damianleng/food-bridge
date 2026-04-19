# FoodBridge

A nutrition-aware meal planning app for diverse US communities. FoodBridge takes your health profile, dietary preferences, and food selections, then generates a personalized 7-day meal plan and itemized grocery list with real pricing — powered by the USDA FoodData Central database and Claude AI.

---

## What It Does

1. **Health Profile** — Enter height, weight, age, sex, activity level, health conditions, and medications
2. **Preferences** — Set weekly budget, zip code, dietary restrictions, allergies, and cuisine preferences
3. **Find Foods** — Search 770K+ USDA foods, scored by nutrient density relative to your personal daily values
4. **7-Day Meal Plan** — Claude AI generates a complete plan respecting your allergies, diet, and medications
5. **Grocery List** — Itemized list with real-time web-searched pricing, grouped by category

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + TypeScript + Vite + TailwindCSS |
| State | Zustand with localStorage persistence |
| Backend | FastAPI (Python 3.12) |
| AI Agent | LangChain + Claude Haiku 4.5 (Anthropic API) |
| Pricing | DuckDuckGo web search + Claude LLM extraction |
| Database | PostgreSQL 16 + USDA FoodData Central |
| DevOps | Docker + Docker Compose |

---

## Prerequisites

- Docker & Docker Compose
- Node.js 19+
- An [Anthropic API key](https://console.anthropic.com)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/damianleng/food-bridge.git
cd food-bridge
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=hackathon
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start the backend and database

```bash
docker compose up --build
```

This starts:
- PostgreSQL on port `5433`
- FastAPI backend on port `8000` (with hot reload)

### 4. Load the USDA database

Download the USDA FoodData Central CSV files from [fdc.nal.usda.gov](https://fdc.nal.usda.gov/download-foods.html) and place them in `database/data/`, then run:

```bash
cd database
python3 load_data.py
```

### 5. Start the frontend

```bash
cd client
npm install
npm run dev
```

Frontend runs at [http://localhost:5173](http://localhost:5173).

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | Database name |
| `ANTHROPIC_API_KEY` | Claude API key for meal plan generation |

Frontend optionally reads `VITE_BACKEND_URL` from `client/.env` (defaults to `http://localhost:8000`).

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/profile` | Create user health profile |
| POST | `/preferences` | Save dietary preferences |
| POST | `/search` | Search USDA food database |
| POST | `/meal-plan` | Generate 7-day meal plan (AI) |
| POST | `/grocery-list` | Generate priced grocery list |
| GET | `/health` | Health check |

---

## Development

Backend code hot-reloads automatically — no rebuild needed after code changes.

To run scripts inside the container:

```bash
docker compose exec backend python3 <script>.py
```

---

## Project Structure

```
food-bridge/
├── backend/
│   ├── api.py            # FastAPI endpoints
│   ├── db.py             # PostgreSQL helpers
│   ├── user.py           # Profile, food search, grocery logic
│   ├── planner.py        # LangChain meal plan agent + pricing
│   ├── nutrition.py      # BMR/TDEE + personalized DV calculations
│   ├── requirements.txt
│   └── Dockerfile
├── client/
│   └── src/
│       ├── screens/      # Onboarding, Preferences, FoodSearch, MealPlan, GroceryList
│       ├── lib/api.ts    # API client
│       └── store/app.ts  # Zustand store
├── database/
│   ├── models.py         # SQLAlchemy schema
│   ├── load_data.py      # USDA CSV bulk loader
│   └── data/             # USDA FDC CSV files (not committed)
├── docker-compose.yml
└── .env.example
```
