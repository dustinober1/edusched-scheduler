FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE MANIFEST.in ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -e .[api]

EXPOSE 8000

CMD ["python", "-m", "edusched.api.main"]
