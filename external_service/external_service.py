from flask import Flask, request, jsonify
import requests
import time
import random
import logging
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
log_stream = 'external_service_stream'

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

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    REQUEST_LATENCY.labels(request.path).observe(request_latency)
    REQUEST_COUNT.labels(request.path, request.method, response.status_code).inc()
    return response

@app.route('/convert', methods=['GET'])
def convert():
    amount = request.args.get('amount')
    base_currency = request.args.get('currency')

    if not amount or not base_currency:
        return jsonify({"error": "Missing required parameters", "amount": amount, "currency": currency}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Invalid amount format"}), 400

    # Simulate delay
    # time.sleep(random.uniform(0.5, 0.7))

    # Use the freecurrencyapi.io service
    api_key = 'fca_live_j805PsM8I5AkfzIqKiTrujwUGnFBMEXAqASwZhZB'
    response = requests.get(f'https://api.freecurrencyapi.com/v1/latest?apikey={api_key}&base_currency={base_currency}&currencies=USD')

    if response.status_code != 200:
        logger.error("Error fetching exchange rate")
        put_log_event("Error fetching exchange rate")
        return jsonify({"error": "Error fetching exchange rate"}), 500

    data = response.json()
    rate = data['data'].get('USD')

    if not rate:
        return jsonify({"error": "Invalid base currency code"}), 400

    converted_amount = amount * rate
    put_log_event(f'Conversion done to USD successfully equaling {converted_amount}')
    return jsonify({"converted_amount_in_usd": converted_amount})

if __name__ == "__main__":
    start_http_server(8001)  # Start Prometheus metrics server
    app.run(host='0.0.0.0', port=5001)