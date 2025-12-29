from fastapi import FastAPI
from app.api.auth import auth_router
from app.api.horizons import horizons_router


app = FastAPI(title="SkyArchive")

app.include_router(auth_router)
app.include_router(horizons_router)
