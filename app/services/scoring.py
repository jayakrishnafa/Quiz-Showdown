from fastapi import APIRouter
from pydantic import BaseModel
import os, json
import redis.asyncio as aioredis
import aio_pika

class AnswerRequest(BaseModel):
    sessionId: str
    userId: str
    questionId: str
    answer: str
    timestamp: int

router = APIRouter()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
amqp_url  = os.getenv("AMQP_URL",  "amqp://guest:guest@localhost/")

redis_client = None
score_xchg   = None

async def init():
    global redis_client, score_xchg
    redis_client = await aioredis.from_url(redis_url)
    try:
        conn = await aio_pika.connect_robust(amqp_url)
        chan = await conn.channel()
        score_xchg = await chan.declare_exchange("scoring", aio_pika.ExchangeType.FANOUT)
        print("Scoring: connected to RabbitMQ")
    except Exception as e:
        score_xchg = None
        print(f"Scoring: RabbitMQ unavailable ({e}), publishing disabled")

@router.post("/answer")
async def submit_answer(req: AnswerRequest):
    r = redis_client
    correct = await r.hget(f"question:{req.questionId}", "correct")
    start   = await r.hget(f"session:{req.sessionId}", "startTime")
    is_correct   = (req.answer == correct)
    response_time = req.timestamp - int(start or 0)
    score        = int(max(0, 1000 - response_time)) if is_correct else 0

    if score_xchg:
        payload = {"sessionId": req.sessionId, "userId": req.userId, "score": score}
        await score_xchg.publish(
            aio_pika.Message(body=json.dumps(payload).encode()),
            routing_key=""
        )
    return {"score": score}
