FROM python:3.13-slim

# OCI standard image labels
ARG DICT_VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

LABEL org.opencontainers.image.title="SYSNET Managed Dictionaries API"
LABEL org.opencontainers.image.description="REST API pro správu řízených slovníků SYSNET"
LABEL org.opencontainers.image.version="${DICT_VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.vendor="SYSNET s.r.o."
LABEL org.opencontainers.image.authors="rjaeger@sysnet.cz"
LABEL org.opencontainers.image.url="https://sysnet.cz"
LABEL org.opencontainers.image.source="https://github.com/sysnetcz/dictionary-management"
LABEL org.opencontainers.image.licenses="AGPL-3.0"

ARG HOME_DIR=/opt/dictionary

RUN mkdir -p ${HOME_DIR}
WORKDIR ${HOME_DIR}

# curl pro HEALTHCHECK; build-essential pro C-extensions v requirements
RUN apt-get -y update \
    && apt-get -y install --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ${HOME_DIR}/

RUN python3 -m pip install --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt

COPY . ${HOME_DIR}

ENV SERVICE_ENVIRONMENT=production \
    DICT_ROOT_PATH=dict \
    DICT_VERSION=${DICT_VERSION} \
    INSTANCE=PROD \
    TZ=Europe/Prague

EXPOSE 8080

RUN chmod +x ./*.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8080/ || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
