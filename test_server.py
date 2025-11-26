"""Minimal test server to diagnose blocking issues."""

from fastapi import FastAPI
import asyncio

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok", "message": "Server is responding"}


@app.get("/test")
async def test():
    await asyncio.sleep(0.1)  # Simulate async work
    return {"test": "passed"}


@app.get("/dashboard/")
async def dashboard():
    return {"dashboard": "loaded", "data": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
