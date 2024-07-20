#!/bin/bash

# Define directories
DB_DATA_DIR="./data_db"
LOGS_DIR="./logs"

# Create directories if they don't exist
mkdir -p $DB_DATA_DIR
mkdir -p $LOGS_DIR

# Pull Docker images
docker pull postgres:13
docker pull prom/prometheus
docker pull grafana/grafana
docker pull prom/cloudwatch-exporter
docker pull amazon/cloudwatch-agent
docker pull drdroid/playbooks
docker pull prom/node-exporter

# Create a default prometheus.yml if it doesn't exist
if [ ! -f ./prometheus.yml ]; then
    cat <<EOL > ./prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node_exporter:9100']
EOL
fi

# Create a default cloudwatch-agent-config.json if it doesn't exist
if [ ! -f ./cloudwatch-agent-config.json ]; then
    cat <<EOL > ./cloudwatch-agent-config.json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "metrics": {
    "namespace": "ECS/Containers",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "usage_active", "rename": "CPUUsageActive", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "memory": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MemoryUsedPercent", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DiskUsedPercent", "unit": "Percent"}
        ],
        "ignore_file_system_types": ["sysfs", "devtmpfs"],
        "metrics_collection_interval": 60
      },
      "diskio": {
        "measurement": [
          {"name": "io_time", "rename": "DiskIOTime", "unit": "Milliseconds"}
        ],
        "metrics_collection_interval": 60
      },
      "swap": {
        "measurement": [
          {"name": "swap_used_percent", "rename": "SwapUsedPercent", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": [
          {"name": "tcp_established", "rename": "TcpEstablished", "unit": "Count"}
        ],
        "metrics_collection_interval": 60
      },
      "net": {
        "measurement": [
          {"name": "bytes_out", "rename": "NetworkBytesOut", "unit": "Bytes"}
        ],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/shared/payment_service.log",
            "log_group_name": "/ecs/fastbite/payment_service",
            "log_stream_name": "{hostname}"
          }
        ]
      }
    }
  }
}
EOL
fi

# Create a default Dockerfile for payment_service if it doesn't exist
if [ ! -f ./Dockerfile ]; then
    cat <<EOL > ./Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
EOL
fi

# Create a default requirements.txt for payment_service if it doesn't exist
if [ ! -f ./requirements.txt ]; then
    cat <<EOL > ./requirements.txt
Flask==2.0.1
psycopg2-binary==2.9.1
boto3==1.17.72
EOL
fi

# Create a default app.py for payment_service if it doesn't exist
if [ ! -f ./app.py ]; then
    cat <<EOL > ./app.py
from flask import Flask, request
import psycopg2
import logging
import os
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='/var/log/shared/payment_service.log', level=logging.INFO)

def get_db_connection():
    conn = psycopg2.connect(
        host="db",
        database="fastbite",
        user="fastbite",
        password="password"
    )
    return conn

@app.route('/pay', methods=['POST'])
def process_payment():
    data = request.json
    amount = data['amount']
    logging.info(f"Received payment request for amount: {amount}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Simulate a delay in DB processing
        time.sleep(2)
        cur.execute("INSERT INTO payments (amount) VALUES (%s)", (amount,))
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Payment processed for amount: {amount}")
        return {"status": "success"}, 200
    except Exception as e:
        logging.error(f"Error processing payment: {e}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOL
fi