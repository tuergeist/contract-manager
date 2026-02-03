FROM python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies and uv
# WeasyPrint dependencies per official docs + glib for gobject
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    # WeasyPrint official dependencies
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libffi-dev \
    # GLib/GObject (required by WeasyPrint's ffi)
    libglib2.0-0 \
    # Fonts
    fonts-liberation \
    && ldconfig \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system -e ".[dev]"

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--reload"]
