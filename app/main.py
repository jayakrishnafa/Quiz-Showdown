import uvicorn
from fastapi import FastAPI

import services.matchmaking as matchmaking
import services.game_session as game_session
import services.scoring as scoring
import services.leaderboard as leaderboard

app = FastAPI(title="Quiz Showdown Backend")

app.include_router(matchmaking.router, prefix="/api/matchmaking", tags=["matchmaking"])
app.include_router(game_session.router, prefix="/api/game-session", tags=["game-session"])
app.include_router(scoring.router, prefix="/api/scoring", tags=["scoring"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["leaderboard"])

app.add_event_handler("startup", matchmaking.init)
app.add_event_handler("startup", game_session.init)
app.add_event_handler("startup", scoring.init)
app.add_event_handler("startup", leaderboard.init)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
