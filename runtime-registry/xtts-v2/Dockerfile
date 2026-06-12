# peakvox/xtts-runtime Dockerfile.
#
# Mirrors runtime-registry/f5-tts-base/Dockerfile (the GPU voice-cloning
# reference) with one posture change: XTTS v2 is CPU-CAPABLE, so the image
# uses a CUDA-enabled PyTorch base for GPU acceleration but the server runs
# fine on CPU when the Docker driver hides the GPU ("Use GPU (CUDA)" OFF).
# A CUDA-built torch runs on CPU; the device is chosen at load time in
# server.py via torch.cuda.is_available().
#
# Image tag: peakvox/xtts-runtime:0.1.0 (matches the descriptor's
# spec.image.repository + tag).

FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Accept the Coqui Public Model License (CPML) non-interactively so the
    # container can download/load the XTTS weights without a TTY prompt. The
    # operator accepts CPML by enabling the (CE-disabled, non-commercial) XTTS
    # model in the catalog. See ADR-0021 §License.
    COQUI_TOS_AGREED=1

# System deps:
#   - ffmpeg: audio decoding (reference clips)
#   - libsndfile1: required by soundfile/torchaudio
#   - build-essential: required for some pip wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer cache for the requirements that
# change less often than the source).
COPY requirements.txt /app/requirements.txt

# coqui-tts (the maintained Idiap fork of the original, unmaintained `TTS`
# package) pulls in transformers + a torch pin. As with F5-TTS, if the
# transitive torch differs from the base image's ABI, re-install torchaudio
# from the matching cu-index so the ABI agrees with whatever torch is installed.
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    CUDA_TAG=$(python3 -c "import torch; v=torch.version.cuda; print('cu' + v.replace('.','') if v else 'cpu')") && \
    echo "torch $(python3 -c 'import torch; print(torch.__version__)') → reinstalling torchaudio for ${CUDA_TAG}" && \
    pip install --no-cache-dir --upgrade torchaudio \
        --index-url "https://download.pytorch.org/whl/${CUDA_TAG}" && \
    python3 -c "import torch, torchaudio; print('ABI OK — torch', torch.__version__, 'torchaudio', torchaudio.__version__)"

# Copy the runtime service entrypoint.
COPY server.py /app/server.py

# The descriptor's spec.service.port is 8000. The runtime driver maps it to a
# host port at run time. The Docker driver passes --gpus only when "Use GPU
# (CUDA)" is ON; with it OFF the GPU is hidden and the server runs on CPU.
EXPOSE 8000

# Healthcheck: probe /health every 10s; the service returns 200 even while the
# model is still loading (liveness only).
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" \
    || exit 1

# The runtime service contract: uvicorn serves the FastAPI app on 0.0.0.0:8000.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
