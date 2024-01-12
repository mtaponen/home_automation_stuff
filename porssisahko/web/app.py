from flask import Flask, jsonify, g
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import requests
import pytz
import logging

import sqlite3
from sqlite3 import Error

app = Flask(__name__)

DATABASE = 'prices.db'
# Set the logging level
app.logger.setLevel(logging.INFO)

# # Configure a stream handler to write logs to stdout
# stream_handler = logging.StreamHandler()
# stream_handler.setLevel(logging.DEBUG)

# # Create a formatter and set it on the stream handler
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# stream_handler.setFormatter(formatter)

# # Add the stream handler to the app's logger
# app.logger.addHandler(stream_handler)

local_tz = pytz.timezone('Europe/Helsinki')
# Singleton to get the SQLite connection (one connection per thread)
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


# Initialize the scheduler
scheduler = BackgroundScheduler(timezone="UTC")

# Function to be executed at 02:00 and 14:00 every day
def make_query():
    # Add your logic for making a query here
    print("Query executed at:", datetime.utcnow())

# Schedule the make_query function every day at 02:00 and 14:00
scheduler.add_job(make_query, 'cron', hour='2,14')
scheduler.start()

# Get data before first call
@app.before_first_request
def before_first_request():
    make_query()

# Get cheapest 3 hours as average
@app.route('/get_cheap_hours', methods=['GET'])
def get_cheap_hours():
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().astimezone(local_tz)

    # Fetch only future rows
    cursor.execute('SELECT * FROM prices WHERE startDate > ? ', (now,))
    rows = cursor.fetchall()

    min_average_index = 0
    min_average = float('inf')

    # Loop through the data and find the three consecutive entries with the lowest average price
    for i in range(len(rows) - 2):
        average_price = (rows[i][2] + rows[i+1][2] + rows[i+2][2]) / 3

        if average_price < min_average:
            min_average = average_price
            min_average_index = i

    # Print the three consecutive entries with the lowest average price
    start_date, end_date, price = rows[min_average_index]
    start_hour =  datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
    response_data = {
        "start_date": start_date,
        "min_average": min_average,
        "hour": start_hour
        }

    # Commit the changes and close the connection
    conn.commit()
    #conn.close()
    return jsonify(response_data)


@app.route('/get_current_price', methods=['GET'])
def get_current_price():
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().astimezone(local_tz)
    # Fetch only future rows
    cursor.execute('SELECT * FROM prices WHERE startDate < ? AND endDate > ? ', (now,now,))
    rows = cursor.fetchall()

    start_date, end_date, price = rows[0]
    response_data = {
        "start_date": start_date,
        "price": price
        }

    # Commit the changes and close the connection
    conn.commit()
    #conn.close()
    return jsonify(response_data)


def make_query():
    app.logger.info("Getting latest price info")
    # Make the GET request - note that api returns timestamps with Z although data is in local time
    url = "https://api.porssisahko.net/v1/latest-prices.json"
    response = requests.get(url)
    data = response.json()

    # # Connect to SQLite database
    conn = get_db()
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            startDate TIMESTAMP,
            endDate TIMESTAMP,
            price FLOAT
        )
    ''')

    # Parse and store the data in the database
    for entry in data["prices"]:
        startDate = datetime.strptime(entry["startDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
        endDate = datetime.strptime(entry["endDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
        price = entry["price"]

        cursor.execute('''
            INSERT INTO prices (startDate, endDate, price)
            VALUES (?, ?, ?)
        ''', (startDate, endDate, price))

    # Delete old data
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    cutoff_time = utc_now - timedelta(days=7)
    cursor.execute('DELETE FROM prices WHERE startDate < ?', (cutoff_time,))

    conn.commit()
    #conn.close()
    app.logger.info("Data initialized.")


# Function to close the SQLite connection
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    # Run the Flask application on port 5000
    app.run(port=5000)



