FROM python:3.14

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    DOCKER=true \
    GIT_PYTHON_REFRESH=quiet

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    curl \
    ffmpeg \
    gcc \
    git \
    libavcodec-dev \
    libavdevice-dev \
    libavformat-dev \
    libavutil-dev \
    libcairo2 \
    libmagic1 \
    libswscale-dev \
    openssh-server \
    xfonts-75dpi \
    xfonts-base \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install --no-install-recommends -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /data
RUN mkdir /data/private

# Private repo: pass a token via --build-arg or mount an SSH agent when building.
RUN git clone https://github.com/ziahka/Nimbus /data/Nimbus

WORKDIR /data/Nimbus

ARG NIMBUS_REF=master
RUN git fetch origin "${NIMBUS_REF}" && git checkout "${NIMBUS_REF}" && git pull origin "${NIMBUS_REF}"

RUN pip install --no-cache-dir --no-warn-script-location --disable-pip-version-check --upgrade -r requirements.txt

CMD ["python", "-m", "nimbus", "--root"]
