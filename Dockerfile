FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV HORUS_ROOT=/app
ENV PYTHONPATH=/app

EXPOSE 3781 8001 8002 8003 8004 8082 11489

CMD ["python", "horus_startup.py", "--start"]
