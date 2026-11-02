FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN adduser --disabled-password --gecos '' api-user

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .
COPY start.sh .

RUN chmod +x start.sh
RUN chown -R api-user:api-user /app

USER api-user

EXPOSE 8000

CMD ["./start.sh"]
