FROM python:3.12-slim

WORKDIR /app

# Copy shared problems library (build context is ./backend/)
COPY shared ./shared

# Install dependencies
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker source
COPY worker/ .

# WORKER_ID is injected at runtime via docker-compose environment
ENV WORKER_ID=worker-default

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
