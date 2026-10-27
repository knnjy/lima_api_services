from http.client import HTTPException

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials

    try:
        # Verify the token with Supabase Auth.
        response = auth_client.auth.get_user(token)
        user = response.user

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
            )

        # The user ID comes from the verified Supabase user.
        user_id = str(user.id)

        # Look up the user's application role.
        result = (
            db_client.table("profiles")
            .select("id, role_id, roles(name)")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        profile = result.data

        if not profile or not profile.get("roles"):
            raise HTTPException(
                status_code=403,
                detail="User profile or role not found",
            )

        role_data = profile["roles"]

        # Supabase relationship results can be a dict
        # or a list, depending on the relationship.
        if isinstance(role_data, list):
            role_data = role_data[0] if role_data else None

        if not role_data or not role_data.get("name"):
            raise HTTPException(
                status_code=403,
                detail="User role not found",
            )

        return {
            "id": user_id,
            "email": user.email,
            "role": role_data["name"],
        }

    except HTTPException:
        raise
    except Exception:
        # Avoid leaking internal database/auth errors.
        raise HTTPException(
            status_code=401,
            detail="Could not authenticate user",
        )


def require_role(*allowed_roles: str):
    def role_checker(
        current_user: dict = Depends(get_current_user),
    ):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource",
            )

        return current_user

    return role_checker