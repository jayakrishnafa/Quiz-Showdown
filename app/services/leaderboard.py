from fastapi import APIRouter
import os, json
import redis.asyncio as aioredis
import aio_pika

router = APIRouter()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
amqp_url  = os.getenv("AMQP_URL",  "amqp://guest:guest@localhost/")

redis_client = None

async def init():
    global redis_client
    redis_client = await aioredis.from_url(redis_url)
    try:
        conn = await aio_pika.connect_robust(amqp_url)
        chan = await conn.channel()
        xchg = await chan.declare_exchange("session-results", aio_pika.ExchangeType.FANOUT)
        q = await chan.declare_queue("", exclusive=True)
        await q.bind(xchg)

        async def on_result(msg: aio_pika.IncomingMessage):
            async with msg.process():
                data = json.loads(msg.body)
                teams, final = data.get("teams", []), data.get("finalScores", {})
                for team in teams:
                    tid   = team.get("id")
                    score = final.get(tid, 0)
                    for p in team.get("players", []):
                        await redis_client.zincrby("leaderboard:global", score, p["userId"])
                        await redis_client.zincrby(f"leaderboard:{p['location']}", score, p["userId"])
        await q.consume(on_result)
        print("Leaderboard: subscribed to session-results")
    except Exception as e:
        print(f"Leaderboard: RabbitMQ unavailable ({e}), updates disabled")

@router.get("/global")
async def global_lb(limit: int = 10):
    raw = await redis_client.zrevrange("leaderboard:global", 0, limit-1, withscores=True)
    return [{"userId": u, "score": int(s)} for u, s in raw]

@router.get("/location/{loc}")
async def location_lb(loc: str, limit: int = 10):
    key = f"leaderboard:{loc}"
    raw = await redis_client.zrevrange(key, 0, limit-1, withscores=True)
    return [{"userId": u, "score": int(s)} for u, s in raw]
