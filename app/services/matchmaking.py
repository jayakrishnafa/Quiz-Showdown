from fastapi import APIRouter
from pydantic import BaseModel
import os, json, uuid, asyncio
import redis.asyncio as aioredis
import aio_pika

class JoinRequest(BaseModel):
    userId: str
    subject: str
    location: str

router = APIRouter()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
amqp_url  = os.getenv("AMQP_URL",  "amqp://guest:guest@localhost/")

redis_client = None
match_xchg    = None

async def init():
    global redis_client, match_xchg
    # Redis always required
    redis_client = await aioredis.from_url(redis_url)
    # RabbitMQ optional
    try:
        conn = await aio_pika.connect_robust(amqp_url)
        chan = await conn.channel()
        match_xchg = await chan.declare_exchange(
            "matchmaking", aio_pika.ExchangeType.FANOUT
        )
        print("Matchmaking: connected to RabbitMQ")
    except Exception as e:
        match_xchg = None
        print(f"Matchmaking: RabbitMQ unavailable, continuing without AMQP ({e})")

@router.post("/join")
async def join(req: JoinRequest):
    r = redis_client
    key = f"queue:{req.subject}"
    await r.lpush(key, json.dumps(req.dict()))
    length = await r.llen(key)

    if length >= 4 and match_xchg:
        raw = await asyncio.gather(*(r.rpop(key) for _ in range(4)))
        players = [json.loads(p) for p in raw]
        teams = [players[:2], players[2:]]
        session_id = str(uuid.uuid4())
        payload = {"sessionId": session_id, "subject": req.subject, "teams": teams}
        await match_xchg.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key=""
        )

    return {"status": "queued", "queuePosition": length}
