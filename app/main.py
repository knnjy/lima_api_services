from fastapi import FastAPI

from app.Authentication import router as authentication_router
from app.IdentityAndAccess.router.profile_router import router as profile_router
from app.LivestockRegistry.router.farm_router import router as farm_crud_router
from app.LivestockRegistry.router.farm_membership_router import router as farm_router
from app.LivestockRegistry.router.animal_router import router as animal_router

app = FastAPI()
app.include_router(authentication_router)
app.include_router(profile_router)
app.include_router(farm_crud_router)
app.include_router(farm_router)
app.include_router(animal_router)
