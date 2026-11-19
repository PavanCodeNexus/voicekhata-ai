FROM python:3.10-slim

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY README.md /app/README.md

WORKDIR /app/backend

ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
