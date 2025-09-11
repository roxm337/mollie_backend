import uvicorn
from fastapi import FastAPI
from .routers import payments
from .db import init_db
from .config import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mollie Payments Service")

# CORS - allow your app domain(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your frontend domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments.router)

@app.on_event("startup")
async def on_startup():
    # init db tables if not using migrations
    await init_db()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=(settings.env != "production"))

