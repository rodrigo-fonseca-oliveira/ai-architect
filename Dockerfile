FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build deps for some libs (pandas, scipy stack minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install pip, then install CPU-only PyTorch wheels first, then sentence-transformers
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio && \
    pip install --no-cache-dir sentence-transformers

# Copy project metadata and install deps
COPY pyproject.toml /app/
RUN python - <<'PY'
import tomllib
with open('pyproject.toml','rb') as f:
    data = tomllib.load(f)
reqs = data.get('project',{}).get('dependencies',[])
print('\n'.join(reqs))
PY
RUN pip install --no-cache-dir -e .

# Copy source
COPY . /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
