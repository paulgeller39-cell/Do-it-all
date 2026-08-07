FROM python:3.11-slim
WORKDIR /app
COPY connector.py /app/connector.py
RUN pip install --no-cache-dir redis websockets aiohttp
ENV PYTHONUNBUFFERED=1
CMD ["python", "connector.py"]
