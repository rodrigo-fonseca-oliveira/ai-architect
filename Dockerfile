FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build deps for some libs (pandas, scipy stack minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Toggle CPU/GPU torch via build arg (cpu or a CUDA tag like cu121)
ARG TORCH_VARIANT=cpu
ENV TORCH_VARIANT=${TORCH_VARIANT}

# Pre-install PyTorch to avoid slow/large CUDA wheels when pulling transitive deps
# For CPU: uses https://download.pytorch.org/whl/cpu
# For CUDA (example cu121): uses https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir -U pip && \
    if [ "$TORCH_VARIANT" = "cpu" ]; then \
      TORCH_INDEX=https://download.pytorch.org/whl/cpu ; \
    else \
      TORCH_INDEX=https://download.pytorch.org/whl/${TORCH_VARIANT} ; \
    fi && \
    pip install --no-cache-dir --index-url ${TORCH_INDEX} \
      torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 || true

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
