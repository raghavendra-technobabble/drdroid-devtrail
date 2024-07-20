from flask import Flask, request
import psycopg2
import logging
import os
import time
from prometheus_client import start_http_server, Summary, Counter, generate_latest
import urllib.parse

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='/var/log/shared/payment_service.log', level=logging.INFO)

# Prometheus metrics
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')
REQUEST_COUNT = Counter('request_count', 'Total request count')

def get_db_connection():
    conn = psycopg2.connect(
        host="db",
        database="fastbite",
        user="fastbite",
        password="password"
    )
    return conn

@app.route('/metrics')
def metrics():
    return generate_latest()

@app.route('/pay', methods=['POST'])
def process_payment():
    REQUEST_COUNT.inc()
    data = request.json
    amount = data['amount']
    logging.info(f"Received payment request for amount: {amount}")
    
    with REQUEST_TIME.time():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Simulate a delay in DB processing
            #time.sleep(2)
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
    # Start Prometheus metrics server
    start_http_server(8000)
    app.run(host='0.0.0.0', port=5000)