# peakvox/kokoro-runtime Dockerfile (R8 reference).
#
# This is the canonical reference shape for every runtime
# service (F5-TTS, XTTS, OpenVoice, Fish, OmniVoice). Future
# runtimes copy this Dockerfile and adjust:
#
#   1. The base image (slim → slim for CPU, runtime for GPU).
#   2. The framework install (requirements.txt).
#   3. The entrypoint (server.py path).
#   4. The EXPOSE port (descriptor's spec.service.port).
#   5. The CMD bind (uvicorn server:app --host 0.0.0.0 --port).
#
# Image tag: peakvox/kokoro-runtime:0.1.0 (matches the descriptor's
# spec.image.repository + tag; spec.image.digest is set by the
# build script after a successful `docker build`).

FROM python:3.11-slim

# Avoid bytecode; force unbuffered stdout/stderr for log streaming.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: ffmpeg is required by the kokoro package for
# audio decoding; espeak-ng is the phonemizer backend; build-essential
# is needed for some of the pip wheels. The image is slim; we add
# only what is strictly required.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        espeak-ng \
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
