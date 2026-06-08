# peakvox/omnivoice-runtime Dockerfile.
#
# Mirrors runtime-registry/kokoro-82m/Dockerfile (R8 reference).
# Adjustments from the Kokoro template:
#   1. Image tag: peakvox/omnivoice-runtime:0.1.0
#      (matches descriptor's spec.image.repository + tag).
#   2. Framework install: omnivoice==0.1.0
#      (replaces kokoro==0.7.16 + spacy).
#   3. No phonemizer system deps (OmniVoice uses Qwen3 tokenizer).
#   4. EXPOSE 8000 (descriptor's spec.service.port).
#   5. CMD: uvicorn server:app --host 0.0.0.0 --port 8000
#      (same as Kokoro — the Runtime Service Contract is stable).

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps:
#   - ffmpeg: required for audio decoding
#   - build-essential: required for some pip wheels (e.g. tokenizers)
#
# The image is slim; we add only what is strictly required. The
# OmniVoice weights are downloaded on first inference; the entrypoint
# can be parameterized to pre-bake the weights for offline deploys.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer cache for the requirements
# that change less often than the source).
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the runtime service entrypoint.
COPY server.py /app/server.py

# The descriptor's spec.service.port is 8000. EXPOSE documents the
# port; the runtime driver maps it to a host port at run time.
EXPOSE 8000

# Healthcheck: probe /health every 10s; the service returns 200
# even when the model is still loading (liveness only).
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" \
    || exit 1

# The runtime service contract: uvicorn serves the FastAPI app on
# 0.0.0.0:8000. The descriptor's spec.service.port must match.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
