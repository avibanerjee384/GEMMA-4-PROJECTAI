import anyio
from fastapi import FastAPI

app = FastAPI()


async def fake_video_streamer():
    for i in range(10):
        yield b"some fake video bytes"
        await anyio.sleep(0)


@app.get("/")
async def main():
    async for chunk in fake_video_streamer():
        yield chunk
