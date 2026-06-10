# peakvox/omnivoice-runtime Dockerfile.
#
# Mirrors runtime-registry/kokoro-82m/Dockerfile (R8 reference).
# Adjustments from the Kokoro template:
#   1. Image tag: peakvox/omnivoice-runtime:0.1.5
#      (matches descriptor's spec.image.repository + tag).
#   2. Framework install: omnivoice==0.1.5
#      (replaces kokoro==0.7.16 + spacy).
#   3. No phonemizer system deps (OmniVoice uses Qwen3 tokenizer).
#   4. EXPOSE 8000 (descriptor's spec.service.port).
#   5. CMD: uvicorn server:app --host 0.0.0.0 --port 8000
#      (same as Kokoro — the Runtime Service Contract is stable).

FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps:
#   - ffmpeg: required for audio decoding
#   - build-essential: required for some pip wheels (e.g. tokenizers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer cache for the requirements
# that change less often than the source).
COPY requirements.txt /app/requirements.txt

# omnivoice upgrades torch via transitive deps. Use the documentation-recommended
# versions (torch 2.8.0) to ensure full CUDA 12.8 support and flex_attention compatibility.
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir --force-reinstall \
        torch==2.8.0+cu128 \
        torchaudio==2.8.0+cu128 \
        torchvision \
        --extra-index-url https://download.pytorch.org/whl/cu128 && \
    python3 -c "import torch, torchaudio, torchvision; print('ABI OK — torch', torch.__version__, 'torchaudio', torchaudio.__version__, 'torchvision', torchvision.__version__)"

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
