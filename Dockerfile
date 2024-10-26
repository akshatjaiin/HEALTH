FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app


# Install pip and dependencies
RUN pip install --upgrade pip
RUN pip install gunicorn uvicorn 

# Copy the requirements file into the container
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/static

RUN rm -rf MUSEUM_BOT/_pycache_

RUN python manage.py migrate --noinput || true

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD  ["gunicorn","MUSEUM_BOT.wsgi:application", "-k", "uvicorn.workers.UvicornWorker",  "--bind", "0.0.0.0:8000"]
