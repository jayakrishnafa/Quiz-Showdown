from fastapi import APIRouter
import os, json, asyncio
import redis.asyncio as aioredis
import aio_pika

router = APIRouter()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
amqp_url  = os.getenv("AMQP_URL",  "amqp://guest:guest@localhost/")

redis_client = None
consume_queue = None

async def init():
    global redis_client, consume_queue
    redis_client = await aioredis.from_url(redis_url)
    try:
        conn = await aio_pika.connect_robust(amqp_url)
        chan = await conn.channel()
        xchg = await chan.declare_exchange("matchmaking", aio_pika.ExchangeType.FANOUT)
        q = await chan.declare_queue("", exclusive=True)
        await q.bind(xchg)
        consume_queue = q
        async def on_match(msg: aio_pika.IncomingMessage):
            async with msg.process():
                data = json.loads(msg.body)
                sid, teams, subject = data["sessionId"], data["teams"], data["subject"]
                key = f"session:{sid}"
                start = int(asyncio.get_event_loop().time() * 1000)
                await redis_client.hset(key, mapping={
                    "subject": subject,
                    "teams": json.dumps(teams),
                    "startTime": str(start)
                })
                await redis_client.publish(
                    key,
                    json.dumps({"type":"START","sessionId":sid,"teams":teams})
                )
        await consume_queue.consume(on_match)
        print("GameSession: subscribed to matchmaking events")
    except Exception as e:
        print(f"GameSession: RabbitMQ unavailable ({e}), matchmaking events disabled")

# no HTTP endpoints here—everything driven via Redis pub/sub
