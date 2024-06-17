import logging
from fastapi import FastAPI, Response
import uvicorn

app = FastAPI()
logger = logging.getLogger(__name__)


@app.get('/oauth')
async def get_code(code: str, state: str):
    logger.info('code: %s, state: %s', code, state)
    return Response(status_code=200)

@app.get('/test')
async def test():
    logger.info('test ok')
    return Response(content="test OK", status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)