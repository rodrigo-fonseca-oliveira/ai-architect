FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml /app/
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r <(python - <<'PY'
import tomllib
import sys
with open('pyproject.toml','rb') as f:
    data = tomllib.load(f)
reqs = data.get('project',{}).get('dependencies',[])
print('\n'.join(reqs))
PY
)

COPY app /app/app
COPY .env.example /app/.env

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
