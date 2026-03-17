import cv2, time, threading, math, psutil
from flask import Flask, Response, jsonify, request
from pymavlink import mavutil
from rplidar import RPLidar

# ================= CONFIG =================
RTSP_URL = "rtsp://192.168.144.25:8554/main.264"
MAV_PORT = "/dev/ttyACM0"
LIDAR_PORT = "/dev/ttyUSB0"

RC_NEUTRAL = 1500
RC_STEP = 50
RC_LIMIT_LOW = 1100
RC_LIMIT_HIGH = 1900

app = Flask(__name__)

# Global States
frame = None
lock = threading.Lock()
mode = "DISCONNECTED"
battery = 0.0
armed = False
yaw_target = RC_NEUTRAL
pitch_target = RC_NEUTRAL
sectors = {"front":0, "left":0, "right":0}
points = []

# ================= TELEMETRY HELPERS =================
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return round(int(f.read()) / 1000, 1)
    except: return 0.0

# ================= CAMERA LOOP (LAG FIXED) =================
def cam_loop():
    global frame
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Set buffer to minimum
    
    while True:
        # Clear buffer: Grab all available frames quickly
        if not cap.grab():
            time.sleep(0.1)
            continue
            
        # Retrieve only the most recent frame
        ret, img = cap.retrieve()
        if not ret:
            continue

        img = cv2.resize(img, (640, 360))
        with lock:
            frame = img

def gen():
    while True:
        with lock:
            if frame is None: continue
            _, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            data = jpg.tobytes()
        yield (b"--frame\r\nContent-Type:image/jpeg\r\n\r\n" + data + b"\r\n")

# ================= MAVLINK LOOP (BATTERY FIXED) =================
try:
    master = mavutil.mavlink_connection(MAV_PORT, baud=115200)
    master.wait_heartbeat()
    # Explicitly request battery/status streams
    master.mav.request_data_stream_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, 2, 1)
except:
    master = None

def mav_loop():
    global mode, battery, armed
    if not master: return
    while True:
        msg = master.recv_match(blocking=False)
        if not msg:
            time.sleep(0.01)
            continue
        if msg.get_type() == "HEARTBEAT":
            mode = mavutil.mode_string_v10(msg)
            armed = master.motors_armed()
        # Check multiple battery message types
        if msg.get_type() == "SYS_STATUS":
            battery = msg.voltage_battery / 1000.0
        elif msg.get_type() == "BATTERY_STATUS":
            if hasattr(msg, 'voltages'):
                battery = msg.voltages[0] / 1000.0

def rc_loop():
    if not master: return
    while True:
        master.mav.rc_channels_override_send(
            master.target_system, master.target_component,
            0,0,0,0,0,0,0,0,0,0,
            int(yaw_target), int(pitch_target),
            0,0,0,0
        )
        time.sleep(0.05)

# ================= LIDAR LOOP =================
def lidar_loop():
    global points, sectors
    try:
        lidar = RPLidar(LIDAR_PORT)
        for scan in lidar.iter_scans():
            pts = []
            sec = {"front":[], "left":[], "right":[]}
            for _, angle, dist in scan:
                a = (angle + 90) % 360
                rad = math.radians(a)
                x = dist * math.cos(rad)
                y = dist * math.sin(rad)
                pts.append((x, y))
                if 60 <= a <= 120: sec["front"].append(dist)
                elif 150 <= a <= 210: sec["left"].append(dist)
                elif a <= 30 or a >= 330: sec["right"].append(dist)
            points = pts
            for k in sec:
                sectors[k] = int(min(sec[k])) if sec[k] else 9999
    except: pass

# ================= FLASK ROUTES =================
@app.route("/")
def home(): return HTML

@app.route("/video")
def video(): return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/data")
def data():
    return jsonify({
        "mode": mode, "battery": round(battery, 2), "armed": armed,
        "front": sectors["front"], "left": sectors["left"], "right": sectors["right"],
        "points": points[:400], "cpu_temp": get_cpu_temp(), "cpu_load": psutil.cpu_percent(),
        "pwm_y": yaw_target, "pwm_p": pitch_target
    })

@app.route("/move", methods=["POST"])
def move():
    global yaw_target, pitch_target
    direction = request.json.get("dir")
    if direction == "up": pitch_target = min(RC_LIMIT_HIGH, pitch_target + RC_STEP)
    elif direction == "down": pitch_target = max(RC_LIMIT_LOW, pitch_target - RC_STEP)
    elif direction == "left": yaw_target = max(RC_LIMIT_LOW, yaw_target - RC_STEP)
    elif direction == "right": yaw_target = min(RC_LIMIT_HIGH, yaw_target + RC_STEP)
    elif direction == "center":
        yaw_target, pitch_target = RC_NEUTRAL, RC_NEUTRAL
    return "OK"

# ================= PI GCS MASTER UI =================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PI GCS MASTER</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #020617; color: #f8fafc; font-family: monospace; }
        .panel { background: rgba(15, 23, 42, 0.9); border: 1px solid #1e293b; backdrop-filter: blur(10px); }
        .neon-text { color: #22d3ee; text-shadow: 0 0 10px rgba(34, 211, 238, 0.4); }
        .d-btn { background: #1e293b; border: 1px solid #334155; display: flex; align-items: center; justify-content: center; width: 60px; height: 60px; border-radius: 12px; cursor: pointer; transition: all 0.1s; color: white; }
        .d-btn:hover { border-color: #22d3ee; }
        .d-btn:active { background: #22d3ee; color: #020617; transform: scale(0.9); }
        #radar { background: radial-gradient(circle, #0f172a 0%, #020617 100%); border-radius: 50%; border: 1px solid #334155; }
    </style>
</head>
<body class="p-4">
    <div class="flex justify-between items-center panel p-4 rounded-2xl mb-4 border-cyan-900/30">
        <div>
            <h1 class="text-xl font-black tracking-tighter neon-text">PI_GCS_MASTER</h1>
            <div class="flex gap-4 text-[10px] text-slate-500 uppercase font-bold">
                <span>CPU: <span id="cpu_load">0</span>%</span>
                <span>TEMP: <span id="cpu_temp">0</span>°C</span>
            </div>
        </div>
        <div class="flex gap-10 items-center">
            <div class="text-right">
                <span class="text-[10px] text-slate-500 block">PWM TARGETS</span>
                <span class="font-mono text-cyan-400">YAW:<span id="py">1500</span> PIT:<span id="pp">1500</span></span>
            </div>
            <div id="status_box" class="px-6 py-2 rounded-lg border border-red-900 bg-red-950/20 text-red-500 text-xs font-bold uppercase tracking-widest">DISARMED</div>
        </div>
    </div>

    <div class="grid grid-cols-12 gap-4">
        <div class="col-span-12 lg:col-span-3 space-y-4">
            <div class="panel p-5 rounded-2xl">
                <h2 class="text-[10px] text-slate-500 mb-4 font-bold uppercase tracking-widest">Telemetry</h2>
                <div class="flex justify-between items-end mb-4">
                    <span class="text-sm text-slate-400">Battery</span>
                    <span id="bat" class="text-3xl font-bold text-white">0.0V</span>
                </div>
                <div class="flex justify-between items-center text-sm">
                    <span class="text-slate-400">Flight Mode</span>
                    <span id="mode" class="px-2 py-1 bg-cyan-500/10 text-cyan-400 rounded">N/A</span>
                </div>
            </div>

            <div class="panel p-5 rounded-2xl">
                <h2 class="text-[10px] text-slate-500 mb-4 font-bold uppercase tracking-widest">Obstacles (mm)</h2>
                <div class="grid grid-cols-3 gap-3 text-center">
                    <div><p class="text-[9px]">LEFT</p><p id="l">--</p></div>
                    <div class="border-x border-slate-800"><p class="text-[9px] text-cyan-500">FRONT</p><p id="f" class="text-cyan-400 font-bold">--</p></div>
                    <div><p class="text-[9px]">RIGHT</p><p id="r">--</p></div>
                </div>
            </div>

            <div class="panel p-5 rounded-2xl flex flex-col items-center">
                <h2 class="text-[10px] text-slate-500 mb-6 font-bold uppercase self-start tracking-widest">Gimbal Control</h2>
                <div class="grid grid-cols-3 gap-3">
                    <div></div><button class="d-btn" onclick="sendMove('up')">▲</button><div></div>
                    <button class="d-btn" onclick="sendMove('left')">◀</button>
                    <button class="d-btn text-[9px] font-bold text-cyan-500 border-cyan-500/30" onclick="sendMove('center')">RST</button>
                    <button class="d-btn" onclick="sendMove('right')">▶</button>
                    <div></div><button class="d-btn" onclick="sendMove('down')">▼</button><div></div>
                </div>
            </div>
        </div>

        <div class="col-span-12 lg:col-span-6">
            <div class="relative rounded-[2rem] overflow-hidden border-2 border-slate-800 bg-black aspect-video shadow-2xl">
                <img src="/video" class="w-full h-full object-cover">
                <div class="absolute bottom-6 left-6 flex items-center gap-3">
                    <div class="flex items-center gap-2 bg-black/60 backdrop-blur px-3 py-1 rounded-full border border-white/10">
                        <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                        <span class="text-[10px] font-bold">LIVE_FEED</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 lg:col-span-3">
            <div class="panel p-5 rounded-2xl h-full flex flex-col items-center">
                <h2 class="text-[10px] text-slate-500 mb-6 font-bold uppercase self-start tracking-widest">Spatial Map</h2>
                <canvas id="radar" width="280" height="280"></canvas>
            </div>
        </div>
    </div>

    <script>
        async function sendMove(dir) {
            await fetch('/move', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dir})});
        }
        window.onkeydown = e => {
            const keys = {"ArrowUp":"up", "ArrowDown":"down", "ArrowLeft":"left", "ArrowRight":"right", " ":"center"};
            if(keys[e.key]) { e.preventDefault(); sendMove(keys[e.key]); }
        };
        const canvas=document.getElementById("radar"), ctx=canvas.getContext("2d");
        function drawRadar(points) {
            ctx.clearRect(0,0,280,280);
            ctx.strokeStyle="rgba(34, 211, 238, 0.1)";
            for(let i=1; i<=3; i++) { ctx.beginPath(); ctx.arc(140, 140, i*40, 0, Math.PI*2); ctx.stroke(); }
            ctx.fillStyle="#22d3ee";
            points.forEach(p => {
                let x = 140 + p[0]/45; let y = 140 + p[1]/45;
                ctx.beginPath(); ctx.arc(x, y, 1.5, 0, Math.PI*2); ctx.fill();
            });
            ctx.fillStyle="#ef4444"; ctx.beginPath(); ctx.arc(140, 140, 3, 0, Math.PI*2); ctx.fill();
        }
        async function update(){
            try {
                const d = await fetch('/data').then(r=>r.json());
                document.getElementById("mode").innerText = d.mode;
                document.getElementById("bat").innerText = d.battery + "V";
                document.getElementById("f").innerText = d.front;
                document.getElementById("l").innerText = d.left;
                document.getElementById("r").innerText = d.right;
                document.getElementById("cpu_temp").innerText = d.cpu_temp;
                document.getElementById("cpu_load").innerText = d.cpu_load;
                document.getElementById("py").innerText = d.pwm_y;
                document.getElementById("pp").innerText = d.pwm_p;
                const sb = document.getElementById("status_box");
                if(d.armed) {
                    sb.innerText = "ARMED"; sb.className = "px-6 py-2 rounded-lg border border-cyan-500 bg-cyan-500/10 text-cyan-400 text-xs font-bold tracking-widest";
                } else {
                    sb.innerText = "DISARMED"; sb.className = "px-6 py-2 rounded-lg border border-red-900 bg-red-950/20 text-red-500 text-xs font-bold tracking-widest";
                }
                drawRadar(d.points);
            } catch(e) {}
        }
        setInterval(update, 200);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    threading.Thread(target=cam_loop, daemon=True).start()
    threading.Thread(target=mav_loop, daemon=True).start()
    threading.Thread(target=lidar_loop, daemon=True).start()
    threading.Thread(target=rc_loop, daemon=True).start()
    # 0.0.0.0 allows external access via Tunneling/VPN
    app.run(host="0.0.0.0", port=5000, threaded=True)
