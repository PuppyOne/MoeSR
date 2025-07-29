from fastapi import FastAPI
from config import is_production
from routers import health, models, run_process, status, tasks


app = FastAPI()

if not is_production:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_methods=["*"],
        allow_origins=["*"],
    )

app.include_router(health.router)
app.include_router(models.router)
app.include_router(run_process.router)
app.include_router(status.router)
app.include_router(tasks.router)
