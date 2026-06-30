FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/ ./backend/

# Create data directories so volume mounts land in the right place
RUN mkdir -p .cognee/data .cognee/system .devbrain

# Default: run the REST API. Override CMD to run the MCP server instead.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
