FROM python:3.12-slim

WORKDIR /app

# Install backend deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install mcp server deps
COPY mcp/requirements.txt ./mcp_requirements.txt
RUN pip install --no-cache-dir -r mcp_requirements.txt

# Copy both backend and mcp source
COPY backend/ ./backend/
COPY mcp/ ./mcp/

WORKDIR /app/backend

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]