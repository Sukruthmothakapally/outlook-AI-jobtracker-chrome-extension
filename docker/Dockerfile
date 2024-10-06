FROM apache/airflow:2.6.2-python3.10

USER root

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && apt-get clean

USER airflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt