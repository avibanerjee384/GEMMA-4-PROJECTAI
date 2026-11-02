import anyio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.get("/", response_class=StreamingResponse)
async def main():
    for i in range(10):
        yield b"some fake video bytes"
        await anyio.sleep(0)
