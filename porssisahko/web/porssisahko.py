from flask import Flask, jsonify, g
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
import requests
import logging

import sqlite3
from sqlite3 import Error

app = Flask(__name__)

DATABASE = 'prices.db'

app.logger.setLevel(logging.INFO)


# Singleton to get the SQLite connection (one connection per thread)
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


# Get data before first call
@app.before_first_request
def before_first_request():
    update_prices()

# Get cheapest 3 hours as average
'''
   Get cheapest 3 hour average.
   if we are already more than 1h into the cheapest period, return the next known cheapest period
'''
@app.route('/cheap_hours', methods=['GET'])
def get_cheap_hours():
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc) - timedelta(hours=1)

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

    conn.commit()
    return jsonify(response_data)

'''
    Get the current price info
    for some reason the time returned is 2 hours off (which is like it was in GMT)
'''
@app.route('/current_price', methods=['GET'])
def get_current_price():
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    # Fetch only future rows
    cursor.execute('SELECT * FROM prices WHERE startDate < ? AND endDate > ? ', (now,now,))
    rows = cursor.fetchall()

    start_date, end_date, price = rows[0]
    response_data = {
        "start_date": start_date,
        "price": price
        }

    conn.commit()
    return jsonify(response_data)

'''
    Getting the price info
    Note that this is not restful in this service as this is GET and it changes state

    api.porssisahko.net returns JSON prices - structure.
    The timestamps are somehow "off". It claims being in UTC (Z in the end of timestamp),
    still the times are almost local time (Helsinki). Last timeslot - however starts at 22 and ends 23.
    it should either be starting at 23 (local time) or 22 (utc time) at winter.
    Lets see how this behaves after DST...
'''
@app.route('/update_prices', methods=['GET'])
def update_prices():
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

    max_end_date = datetime(1, 1, 1)
    # Parse and store the data in the database
    for entry in data["prices"]:
        startDate = datetime.strptime(entry["startDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
        endDate = datetime.strptime(entry["endDate"], "%Y-%m-%dT%H:%M:%S.%fZ")
        max_end_date = max(max_end_date, endDate)
        price = entry["price"]

        cursor.execute('''
            INSERT INTO prices (startDate, endDate, price)
            VALUES (?, ?, ?)
        ''', (startDate, endDate, price))

    # Delete old data
    utc_now = datetime.now(timezone.utc)
    cutoff_time = utc_now - timedelta(days=7)
    cursor.execute('DELETE FROM prices WHERE startDate < ?', (cutoff_time,))

    conn.commit()
    app.logger.info(f"Data initialized up to {max_end_date.strftime('%Y-%m-%d %H:%M')}")
    return jsonify({"updated_to": max_end_date})


# Function to close the SQLite connection
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    scheduler = BackgroundScheduler(timezone="Europe/Helsinki")
    # Prices should be available at 14:00 each day. 16:00 as a backup if it was late
    scheduler.add_job(update_prices, 'cron', hour='14,16')
    scheduler.start()

    # Run the Flask application on port 5000
    app.run(port=5000)


