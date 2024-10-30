from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from concurrent.futures import ThreadPoolExecutor
import asyncio

from routers.chat_router import router

# Khởi tạo FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm middleware Session
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.include_router(router, prefix="/api")

# Tạo một ThreadPoolExecutor
executor = ThreadPoolExecutor()  # Điều chỉnh số worker theo nhu cầu

def long_running_task(n):
    import time
    time.sleep(n)  # Giả lập tác vụ dài
    return f"Task completed after {n} seconds"

@app.get("/run-task/{seconds}")
async def run_task(seconds: int):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, long_running_task, seconds)
    return {"result": result}

@app.post("/api/webhook")
async def webhook(request: Request, token):
    body = await request.json()
    print(body)
# Chạy ứng dụng bằng Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000,reload=True)
