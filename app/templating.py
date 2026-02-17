"""Jinja2 template configuration."""

from fastapi.templating import Jinja2Templates

from app.config import settings

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))
