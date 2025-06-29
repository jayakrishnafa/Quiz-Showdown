Quiz Showdown Backend

A set of FastAPI microservices powering a real-time, scalable 2v2 quiz battle platform.


Getting Started:

1. Install dependencies:
   pip install -r requirements.txt

2. Set environment variables:
   REDIS_URL (default: redis://localhost:6379/0)
   AMQP_URL  (default: amqp://guest:guest@localhost/)

3. Run the server:
   uvicorn main:app --reload --port 8000

4. Health check:
   GET http://localhost:8000/health

API Endpoints:

Matchmaking:
POST /api/matchmaking/join

Game Session:
(driven via Redis Pub/Sub, no public HTTP endpoints)

Scoring:
POST /api/scoring/answer

Leaderboard:
GET /api/leaderboard/global
GET /api/leaderboard/location/{country}

Notes:
- If RabbitMQ is unavailable, services still serve HTTP but skip AMQP.
- Ensure Redis is running before starting.
- For production, use an API gateway and autoscale pods behind it.
