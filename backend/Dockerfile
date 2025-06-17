FROM python:3.11-slim

RUN useradd -m appuser

WORKDIR /app

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download ru_core_news_sm

COPY . .

USER appuser