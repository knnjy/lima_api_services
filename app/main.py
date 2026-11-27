import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.Authentication import router as authentication_router
from app.IdentityAndAccess.router.profile_router import router as profile_router
from app.Farm.FarmManagement.router.farm_router import router as farm_crud_router
from app.Farm.FarmMemberships.router.farm_membership_router import router as farm_router
from app.LivestockRegistry.router.animal_router import router as animal_router
from app.LivestockRegistry.router.animal_group_router import router as animal_group_router
from app.LivestockRegistry.router.species_router import router as species_router
from app.Farm.FarmInvitations.router.farm_invitation_router import (
    accept_router as farm_invitation_accept_router,
    router as farm_invitation_router,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
frontend_url = os.getenv("FRONTEND_URL", "").strip()
if frontend_url:
    parsed_frontend_url = urlsplit(frontend_url)
    if (
        parsed_frontend_url.scheme not in ("http", "https")
        or not parsed_frontend_url.netloc
    ):
        raise RuntimeError("FRONTEND_URL must be an absolute HTTP(S) URL")
    frontend_origin = f"{parsed_frontend_url.scheme}://{parsed_frontend_url.netloc}"
else:
    frontend_origin = None

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin else [],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(authentication_router)
app.include_router(profile_router)
app.include_router(farm_crud_router)
app.include_router(farm_router)
app.include_router(animal_router)
app.include_router(animal_group_router)
app.include_router(species_router)
app.include_router(farm_invitation_router)
app.include_router(farm_invitation_accept_router)
