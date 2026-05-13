FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY wxbot wxbot
COPY scripts scripts
COPY .env.example .env.example

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "wxbot.main:app", "--host", "0.0.0.0", "--port", "8000"]

