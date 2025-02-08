'''
Copyright (c) 2025, DMBK.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions, and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions, and the following disclaimer in the documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''

import serial
import time
import sqlite3
import threading
import os
from flask import Flask, request, jsonify

# Load API Key from environment variable
API_KEY = "fakepassword" # Change this!

# Initialize Flask App
app = Flask(__name__)

# Configure serial connection
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except Exception as e:
    print(f"Error: Unable to connect to modem: {e}")
    exit(1)

# Initialize SQLite database
conn = sqlite3.connect("sms.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    timestamp TEXT,
    message TEXT
)''')
conn.commit()

def send_at_command(command, wait=1):
    """Send an AT command and return response."""
    ser.write((command + "\r\n").encode())
    time.sleep(wait)
    return ser.read(ser.inWaiting()).decode()

def check_unread_messages():
    """Polls the SIM for unread messages, stores them, and deletes them."""
    response = send_at_command('AT+CMGL="REC UNREAD"')
    if "+CMGL:" in response:
        messages = response.split("\n")
        for i in range(len(messages)):
            if messages[i].startswith("+CMGL:"):
                parts = messages[i].split(",")
                msg_id = parts[0].split(":")[1].strip()
                sender = parts[2].strip('"')
                timestamp = parts[4].strip('"')
                message = messages[i + 1].strip()

                # Store message in database
                cursor.execute("INSERT INTO messages (sender, timestamp, message) VALUES (?, ?, ?)",
                               (sender, timestamp, message))
                conn.commit()

                print(f"Saved message from {sender}: {message}")

                # Delete message from SIM
                send_at_command(f"AT+CMGD={msg_id}")

def poll_messages():
    """Background thread that checks for unread messages every 30-60 seconds."""
    while True:
        try:
            check_unread_messages()
        except Exception as e:
            print(f"Error polling messages: {e}")
        time.sleep(30)  # Poll every 30 seconds

def send_sms(phone_number, message):
    """Send an SMS message."""
    send_at_command("AT+CMGF=1")  # Set text mode
    send_at_command(f'AT+CMGS="{phone_number}"')  # Set recipient
    ser.write((message + "\x1A").encode())  # Send message + CTRL+Z
    time.sleep(3)
    response = ser.read(ser.inWaiting()).decode()
    return "OK" in response

def check_api_key():
    """Middleware to check the API key in the request headers."""
    request_key = request.headers.get("X-API-KEY")
    if request_key != API_KEY:
        return jsonify({"error": "Unauthorized access"}), 401

# Flask API Endpoints
@app.route("/messages", methods=["GET"])
def get_messages():
    """Fetch all stored messages."""
    auth_response = check_api_key()
    if auth_response:
        return auth_response

    cursor.execute("SELECT * FROM messages")
    messages = [{"id": row[0], "sender": row[1], "timestamp": row[2], "message": row[3]} for row in cursor.fetchall()]
    return jsonify(messages)

@app.route("/send_sms", methods=["POST"])
def api_send_sms():
    """API to send SMS via modem."""
    auth_response = check_api_key()
    if auth_response:
        return auth_response

    data = request.get_json()
    phone_number = data.get("phone_number")
    message = data.get("message")

    if not phone_number or not message:
        return jsonify({"error": "phone_number and message are required"}), 400

    if send_sms(phone_number, message):
        return jsonify({"success": f"Message sent to {phone_number}"})
    else:
        return jsonify({"error": "Failed to send SMS"}), 500

# Start background SMS polling thread
threading.Thread(target=poll_messages, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
