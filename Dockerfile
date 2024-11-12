FROM nvidia/cuda:11.8.0-base-ubuntu22.04

# Set environment variables for build
#ENV DEBIAN_FRONTEND=noninteractive \
#    PYTHONDONTWRITEBYTECODE=1 \
#    PYTHONUNBUFFERED=1 \
#    PIP_NO_CACHE_DIR=1

WORKDIR /app/ProteinMPNN

# install Python using UV
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv venv --python 3.10 \
    && uv pip install --index-url https://download.pytorch.org/whl/cu118 \
    torch==2.0.1  \
    torchvision==0.15.2  \
    torchaudio==2.0.2


#RUN apt-get -q update \
#    && apt-get install --no-install-recommends -y \
#    python3.10 \
#    python3-pip \
#    && python3.10 -m pip install -q -U --no-cache-dir pip \
#    && rm -rf /var/lib/apt/lists/* \
#    && apt-get autoremove -y \
#    && apt-get clean \
#    && pip install --index-url https://download.pytorch.org/whl/cu118 \
#    torch==2.0.1  \
#    torchvision==0.15.2  \
#    torchaudio==2.0.2


COPY . .

