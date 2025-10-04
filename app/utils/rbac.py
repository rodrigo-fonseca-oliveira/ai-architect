from fastapi import Request, HTTPException, status, Depends

ROLE_ORDER = {"guest": 0, "analyst": 1, "admin": 2}


def parse_role(request: Request) -> str:
    role = request.headers.get("X-User-Role", "guest").lower()
    return role if role in ROLE_ORDER else "guest"


def require_role(min_role: str):
    min_val = ROLE_ORDER.get(min_role, 0)

    async def dependency(role: str = Depends(parse_role)):
        if ROLE_ORDER.get(role, 0) < min_val:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return role

    return dependency


def is_allowed_grounded_query(role: str) -> bool:
    return ROLE_ORDER.get(role, 0) >= ROLE_ORDER["analyst"]


def is_allowed_agent_step(role: str, step: str) -> bool:
    if step == "fetch":
        return ROLE_ORDER.get(role, 0) >= ROLE_ORDER["analyst"]
    return True
