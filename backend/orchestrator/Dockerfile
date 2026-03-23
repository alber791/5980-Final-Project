FROM python:3.12-slim

WORKDIR /app

# Copy shared problems library (build context is ./backend/)
COPY shared ./shared

# Install dependencies
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy orchestrator source
COPY orchestrator/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
