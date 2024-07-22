from flask import Flask, request, jsonify
import time
import random
import logging
import requests
from prometheus_client import Counter, Histogram, start_http_server
import boto3
import os

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('request_count', 'App Request Count', ['endpoint', 'method', 'http_status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['endpoint'])

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# AWS CloudWatch configuration
aws_region = os.environ['AWS_DEFAULT_REGION']
log_group = 'payment_service_log_group'
log_stream = 'payment_service_stream'

client = boto3.client('logs', region_name=aws_region)

# Create log groups if they do not exist
def create_log_group():
    response = client.describe_log_groups(logGroupNamePrefix=log_group)
    if not any(group['logGroupName'] == log_group for group in response['logGroups']):
        client.create_log_group(logGroupName=log_group)
        print(f"Created log group: {log_group}")

# Create log stream if it does not exist
def create_log_stream(log_group_name, log_stream_name):
    response = client.describe_log_streams(logGroupName=log_group_name, logStreamNamePrefix=log_stream_name)
    if not any(stream['logStreamName'] == log_stream_name for stream in response['logStreams']):
        client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
        print(f"Created log stream: {log_stream_name}")

create_log_group()
create_log_stream(log_group, log_stream)

def put_log_event(message):
    timestamp = int(time.time() * 1000)
    client.put_log_events(
        logGroupName=log_group,
        logStreamName=log_stream,
        logEvents=[{'timestamp': timestamp, 'message': message}]
    )

external_service_url = "http://external_service:5001"

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    REQUEST_LATENCY.labels(request.path).observe(request_latency)
    REQUEST_COUNT.labels(request.path, request.method, response.status_code).inc()
    return response

# Scenario 1: Simulate Slow Response Times
@app.route('/pay', methods=['POST'])
def pay():
    amount = request.json.get('amount')
    currency = request.json.get('currency')

    # Simulate delay
    time.sleep(random.uniform(0.5, 2.0))

    # Fetch exchange rate from external service
    response = requests.get(f'{external_service_url}/convert?amount={amount}&currency={currency}')
    if response.status_code != 200:
        logger.error("External service error")
        put_log_event("External service error")
        return jsonify({"error": "External service error"}), 500
    print(response)
    converted_amount = response.json().get('converted_amount_in_usd')
    put_log_event(f'Payment done in USD successfully of {converted_amount}')
    return jsonify({"status": "success", "converted_amount": converted_amount}), 200

# # Scenario 2: Simulate Error Responses
# @app.route('/process', methods=['POST'])
# def process():
#     if random.random() < 0.3:  # 30% chance to trigger an error
#         logger.error("Processing error occurred")
#         put_log_event("Processing error occurred")
#         return jsonify({"error": "Processing error"}), 500
#     return jsonify({"status": "processed"}), 200

if __name__ == "__main__":
    start_http_server(8000)  # Start Prometheus metrics server
    app.run(host='0.0.0.0', port=5000)