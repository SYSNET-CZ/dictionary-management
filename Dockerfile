# FROM python:3.9-bullseye
FROM python:3.9-slim

ARG HOME_DOR=/opt/dictionary

RUN mkdir -p ${HOME_DOR}
WORKDIR ${HOME_DOR}

COPY requirements.txt ${HOME_DOR}/

ENV SERVICE_ENVIRONMENT=production

RUN python -m pip install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . ${HOME_DOR}

EXPOSE 8080

CMD ["gunicorn", "app:app", "--preload", "-w", "4", "-t", "120", "-b", "0.0.0.0:8080"]
# CMD ["gunicorn", "app:app", "-w", "4", "-t", "120", "-b", "0.0.0.0:8080"]