FROM python:3.8.2-slim-buster

WORKDIR /app

# Setup & build
COPY requirements.txt .
COPY gunicorn.conf.py .
RUN pip install -r requirements.txt
COPY server ./server

CMD gunicorn -c gunicorn.conf.py "server:app"
