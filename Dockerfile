FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
ca-certificates \
curl \
libpq-dev \
build-essential \
&& rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_PYTHON=3.12

COPY ./pyproject.toml ./uv.lock* ./

RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8002

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
