FROM python:3-slim

LABEL cz.sysnet.vendor="SYSNET s.r.o."
LABEL cz.sysnet.image.authors="rjaeger@sysnet.cz"
LABEL description="SYSNET Controlled Dictionaries"

ARG HOME_DIR=/opt/dictionary

RUN mkdir -p ${HOME_DIR}
WORKDIR ${HOME_DIR}

RUN apt-get -y update; apt-get -y install curl

COPY requirements.txt ${HOME_DIR}


ENV SERVICE_ENVIRONMENT=production \
    API_ROOT_PATH=dict \
    INSTANCE=PROD \
    PATH="$PATH:${HOME_DIR}" \
    TZ=Europe/Prague

RUN python3 -m pip install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ${HOME_DIR}

EXPOSE 8080

RUN chmod +x ./*.sh

RUN cd ${HOME_DIR}
ENTRYPOINT ["/bin/bash", "/opt/dictionary/docker-entrypoint.sh"]
