import os
from fastapi import APIRouter, Request
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
            "project_guide_enabled": os.getenv("PROJECT_GUIDE_ENABLED", "").lower()
            in ("1", "true", "yes", "on"),
        },
    )
