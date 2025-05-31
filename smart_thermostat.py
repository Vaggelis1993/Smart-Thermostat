import time
import board
import adafruit_dht
import paho.mqtt.client as mqtt
import json
import uuid
import RPi.GPIO as GPIO

# Ρυθμίσεις για τα LEDs (προσομοίωση θέρμανσης)
GREEN_LED_PIN = 27   # Πράσινο LED - θέρμανση ενεργή
RED_LED_PIN = 22     # Κόκκινο LED - θέρμανση ανενεργή
GPIO.setmode(GPIO.BCM) 
GPIO.setup(GREEN_LED_PIN, GPIO.OUT) 
GPIO.output(GREEN_LED_PIN, GPIO.LOW)
GPIO.setup(RED_LED_PIN, GPIO.OUT)
GPIO.output(RED_LED_PIN, GPIO.LOW)

# MQTT settings
MQTT_BROKER = "192.168.1.12" # Διεύθυνση του MQTT broker
MQTT_PORT = 1883# Default port για MQTT
MQTT_TOPIC = "home_status" # Topic για δημοσίευση μετρήσεων
MQTT_RECEIVE_TOPIC = "heating/control" # Topic για έλεγχο κατάστασης θέρμανσης
DEVICE_ID = "rasp_zero_thermostat" # Αναγνωριστικό συσκευής

# Αρχικοποίηση αισθητήρα
sensor = adafruit_dht.DHT21(board.D4)

# Συνάρτηση που καλείται όταν γίνεται σύνδεση στον MQTT broker
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code:", rc)
    client.subscribe(MQTT_RECEIVE_TOPIC) # Εγγραφή στο topic για έλεγχο θέρμανσης


# Συνάρτηση που καλείται όταν λαμβάνεται μήνυμα από το MQTT
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode().strip().upper()
        print("Received:", payload)

        if payload == "ON":
            GPIO.output(RED_LED_PIN, GPIO.LOW)
            GPIO.output(GREEN_LED_PIN, GPIO.HIGH)
            print("LED ON - Heating ON")
        elif payload == "OFF":
            GPIO.output(GREEN_LED_PIN, GPIO.LOW)
            GPIO.output(RED_LED_PIN, GPIO.HIGH)
            print("LED OFF - Heating OFF")

    except Exception as e:
        print("Error handling message:", e)

# Δημιουργία MQTT client και ρύθμιση callbacks
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()   # Εκκίνηση του MQTT client σε background thread

try:
    while True:
        try:
            # Ανάγνωση θερμοκρασίας και υγρασίας από τον αισθητήρα
            temperature = sensor.temperature
            humidity = sensor.humidity
            # Δημιουργία JSON μετρήσεων
            if temperature and humidity:
                data = {
                    "device_id": DEVICE_ID,
                    "temperature": {"value": temperature, "unit": "°C"},
                    "humidity": {"value": humidity, "unit": "%"}
                }
                payload = json.dumps(data)
                # Δημοσίευση στο MQTT broker
                client.publish(MQTT_TOPIC, payload)
                print("Published:", payload)
            else:
                print("Failed to read from sensor")

        except RuntimeError as e:
            print("Sensor error:", e.args[0])

        time.sleep(10) # Καθυστέρηση μεταξύ μετρήσεων (τουλάχιστον 2 sec για τον σθυγκεκριμένο αθσθητήρα)

except KeyboardInterrupt:
    # Καθαρισμός και ασφαλής τερματισμός
    print("Exiting...")
    GPIO.cleanup()
    sensor.exit()
    client.loop_stop()
    client.disconnect()

