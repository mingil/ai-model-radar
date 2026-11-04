FROM python:3.11-slim

ENV TZ=Asia/Seoul
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8500

RUN apt-get update && apt-get install -y --no-install-recommends tzdata curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN mkdir -p /app/data /app/logs \
    && chmod -R 777 /app/data /app/logs

EXPOSE 8500

HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

CMD ["python", "-u", "-m", "src.app"]
