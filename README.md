# Hackathon Project

> Work in progress

## Tech Stack

### Frontend (`/client`)
- React + TypeScript
- Vite
- TailwindCSS
- Axios

### Backend (`/server`)
- Python + FastAPI
- Docker Compose
- PostgreSQL

### Agent (`/agent`)
- LangChain
- Google Gemini
- MongoDB (vector DB)

## Getting Started

### Prerequisites
- Node.js
- Python 3.10+
- Docker + Docker Compose

### Setup

1. Clone the repo and copy the env file:
   ```bash
   cp .env.example .env
   ```

2. Start backend services:
   ```bash
   docker compose up
   ```

3. Start the frontend:
   ```bash
   cd client
   npm install
   npm run dev
   ```

4. Start the agent:
   ```bash
   cd agent
   pip install -r requirements.txt
   python main.py
   ```