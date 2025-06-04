# based on: https://github.com/docker/awesome-compose/blob/master/flask/app/Dockerfile

FROM --platform=$BUILDPLATFORM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y spim bubblewrap && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

COPY . .

CMD ["python3", "app.py"]