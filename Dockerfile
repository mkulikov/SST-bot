FROM python:3.12-slim

WORKDIR /app

# system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends sqlite3 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/data

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "bot.py"]