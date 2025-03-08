from flask import Flask, render_template, request, jsonify
import mysql.connector
from collections import deque

app = Flask(__name__)

# Connect to MySQL
db = mysql.connector.connect(host="localhost", user="root", password="123456", database="smart_parking")
cursor = db.cursor()

# Initialize Waiting Queue
waiting_queue = deque()

# Function to initialize parking slots
def initialize_parking_slots(total_slots=5):
    cursor.execute("DELETE FROM ParkingSlots")  # Reset Table
    for slot in range(1, total_slots + 1):
        cursor.execute("INSERT INTO ParkingSlots (slot_id, status) VALUES (%s, 'Available')", (slot,))
    db.commit()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/get_parking_status', methods=['GET'])
def get_parking_status():
    cursor.execute("SELECT * FROM ParkingSlots")
    slots = cursor.fetchall()
    
    cursor.execute("SELECT vehicle_number FROM WaitingQueue")
    queue = cursor.fetchall()

    return jsonify({"slots": slots, "queue": [q[0] for q in queue]})

@app.route('/park_vehicle', methods=['POST'])
def park_vehicle():
    vehicle_number = request.json['vehicle_number']

    cursor.execute("SELECT slot_id FROM ParkingSlots WHERE status='Available' ORDER BY slot_id ASC LIMIT 1")
    slot = cursor.fetchone()

    if slot:
        slot = slot[0]
        cursor.execute("UPDATE ParkingSlots SET vehicle_number=%s, status='Occupied' WHERE slot_id=%s",
                       (vehicle_number, slot))
        db.commit()
        return jsonify({"message": f"Vehicle {vehicle_number} parked at slot {slot}", "status": "success"})
    else:
        waiting_queue.append(vehicle_number)
        cursor.execute("INSERT INTO WaitingQueue (vehicle_number) VALUES (%s)", (vehicle_number,))
        db.commit()
        return jsonify({"message": "Parking full, added to waiting queue.", "status": "waiting"})

@app.route('/remove_vehicle', methods=['POST'])
def remove_vehicle():
    vehicle_number = request.json['vehicle_number']

    cursor.execute("SELECT slot_id FROM ParkingSlots WHERE vehicle_number=%s", (vehicle_number,))
    slot = cursor.fetchone()

    if slot:
        slot = slot[0]
        cursor.execute("UPDATE ParkingSlots SET vehicle_number=NULL, status='Available' WHERE slot_id=%s", (slot,))
        db.commit()

        if waiting_queue:
            next_vehicle = waiting_queue.popleft()
            cursor.execute("DELETE FROM WaitingQueue WHERE vehicle_number=%s", (next_vehicle,))
            cursor.execute("UPDATE ParkingSlots SET vehicle_number=%s, status='Occupied' WHERE slot_id=%s",
                           (next_vehicle, slot))
            db.commit()
            return jsonify({"message": f"Vehicle {vehicle_number} left. {next_vehicle} parked in slot {slot}", "status": "updated"})

        return jsonify({"message": f"Vehicle {vehicle_number} left. Slot {slot} is now available.", "status": "success"})
    else:
        return jsonify({"message": f"Vehicle {vehicle_number} not found!", "status": "error"})

if __name__ == '__main__':
    initialize_parking_slots(5)  # Initialize 5 slots
    app.run(debug=True)
