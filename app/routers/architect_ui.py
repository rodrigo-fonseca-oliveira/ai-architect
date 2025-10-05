from typing import Optional
import os

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/architect/ui", response_class=HTMLResponse, tags=["Architect"])
def get_ui(request: Request):
    return templates.TemplateResponse(
        "architect_form.html",
        {
            "request": request,
            "modes": ["guide", "brainstorm"],
            "project_guide_enabled": os.getenv("PROJECT_GUIDE_ENABLED", "").lower()
            in ("1", "true", "yes", "on"),
        },
    )


@router.post("/architect/ui", response_class=HTMLResponse, tags=["Architect"])
def post_ui(
    request: Request,
    question: str = Form(..., min_length=3),
    mode: str = Form(...),
    grounded: Optional[str] = Form(None),
):
    import requests

    payload = {"question": question, "mode": mode}
    if mode == "brainstorm":
        payload["grounded"] = True if grounded == "on" else False

    try:
        resp = requests.post(
            f"http://localhost:{os.getenv('PORT', 8000)}/architect", json=payload
        )
        data = resp.json()
        status = resp.status_code
    except Exception as e:
        data = {"error": str(e)}
        status = 500

    return templates.TemplateResponse(
        "architect_result.html", {"request": request, "data": data, "status": status}
    )
