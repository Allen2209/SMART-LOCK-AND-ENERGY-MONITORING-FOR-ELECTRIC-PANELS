import network
import socket
from machine import Pin, UART, PWM
import time
import urequests

# =========================
# CONTROL PIN
# =========================
control = Pin(15, Pin.OUT)
control.value(0)

# =========================
# SERVO
# =========================
servo = PWM(Pin(16))
servo.freq(50)

def set_angle(angle):
    duty = int(1638 + (angle / 180) * 8192)
    servo.duty_u16(duty)

set_angle(0)

# =========================
# UART
# =========================
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

voltage = 0
current = 0
power = 0
energy = 0
fault = False

# =========================
# LOG SYSTEM
# =========================
log = []

def add_log(msg):
    t = time.localtime()
    entry = "{:02d}:{:02d}:{:02d} {}".format(t[3], t[4], t[5], msg)
    log.insert(0, entry)
    if len(log) > 10:
        log.pop()

# =========================
# NTFY ALERT
# =========================
def send_alert(msg):
    try:
        urequests.post("https://ntfy.sh/smart_iot_panel", data=msg)
    except:
        pass

# =========================
# WIFI
# =========================
ssid = "SAM"
password = "Sam@jesuS0922"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to WiFi...")
while not wlan.isconnected():
    time.sleep(1)

ip = wlan.ifconfig()[0]
print("👉 http://" + ip)

# =========================
# DASHBOARD UI
# =========================
def webpage(state):
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {{
    margin:0;
    font-family:Arial;
    background:#f4f6f9;
    display:flex;
}}

.sidebar {{
    width:200px;
    background:#1f2937;
    color:white;
    padding:20px;
    height:100vh;
}}

.sidebar h2 {{
    color:#38bdf8;
}}

.sidebar p {{
    margin:12px 0;
    color:#cbd5e1;
}}

.main {{
    flex:1;
    padding:20px;
}}

.cards {{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:10px;
}}

.card {{
    background:white;
    padding:12px;
    border-radius:8px;
}}

.value {{
    font-size:18px;
    margin-top:5px;
}}

.status {{
    margin-top:15px;
    padding:10px;
    background:white;
    border-radius:8px;
}}

.buttons {{
    margin-top:15px;
}}

button {{
    padding:10px 15px;
    margin:5px;
    border:none;
    border-radius:6px;
}}

.unlock {{background:#16a34a;color:white}}
.lock {{background:#dc2626;color:white}}

.logs {{
    margin-top:15px;
    background:white;
    padding:10px;
    border-radius:8px;
    max-height:150px;
    overflow-y:auto;
}}
</style>
</head>

<body>

<div class="sidebar">
<h2>⚡ Panel</h2>
<p>Dashboard</p>
<p>Status</p>
<p>Logs</p>
</div>

<div class="main">

<h2>Smart Electrical Panel</h2>

<div class="cards">
<div class="card">Voltage<div class="value">{voltage} V</div></div>
<div class="card">Current<div class="value">{current} A</div></div>
<div class="card">Power<div class="value">{power} W</div></div>
<div class="card">Energy<div class="value">{energy} kWh</div></div>
</div>

<div class="status">
Status: <b>{state}</b><br>
Fault: {"YES" if fault else "NO"}
</div>

<div class="buttons">
<a href="/unlock"><button class="unlock">UNLOCK</button></a>
<a href="/lock"><button class="lock">LOCK</button></a>
</div>

<div class="logs">
<h3>Recent Logs</h3>
{"<br>".join(log)}
</div>

</div>

</body>
</html>
"""

# =========================
# SERVER (FIXED)
# =========================
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 🔥 FIX
server.bind(addr)
server.listen(1)

state = "LOCKED"

# =========================
# MAIN LOOP
# =========================
while True:
    try:
        # Read UART
        if uart.any():
            try:
                data = uart.readline().decode().strip()
                v, c, p, e, f = data.split(',')
                voltage = float(v)
                current = float(c)
                power = float(p)
                energy = float(e)
                fault = (f == "1" or f == "true")
            except:
                pass

        cl, addr = server.accept()
        req = cl.recv(1024).decode()

        # UNLOCK
        if '/unlock' in req:
            control.value(1)
            set_angle(90)
            state = "UNLOCKED"
            add_log("Door Unlocked")
            send_alert("🔓 UNLOCKED")

        # LOCK
        elif '/lock' in req:
            control.value(0)
            set_angle(0)
            state = "LOCKED"
            add_log("Door Locked")
            send_alert("🔒 LOCKED")

        # FAULT
        if fault:
            control.value(0)
            set_angle(0)
            state = "FAULT-LOCKED"
            add_log("FAULT DETECTED")
            send_alert("⚠️ FAULT")

        # Send response
        cl.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(webpage(state))
        cl.close()

    except Exception as e:
        print("Error:", e)
        try:
            cl.close()
        except:
            pass