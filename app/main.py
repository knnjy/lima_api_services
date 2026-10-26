from fastapi import FastAPI

from app.Authentication import router as authentication_router
from app.LivestockRegistry.controllers.farm_controllers import router as farm_router

app = FastAPI()
app.include_router(authentication_router)
app.include_router(farm_router)