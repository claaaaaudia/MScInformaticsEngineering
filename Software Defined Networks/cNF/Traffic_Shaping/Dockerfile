FROM python:3.11-slim

RUN apt-get update && apt-get install -y iproute2 && rm -rf /var/lib/apt/lists/*
RUN pip install pyyaml

WORKDIR /app
COPY traffic_shaping.py .
COPY traffic_shaping.yaml .

CMD ["python3", "traffic_shaping.py"]
