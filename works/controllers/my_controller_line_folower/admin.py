from flask import Flask, render_template, jsonify, request
import os, time

app = Flask(__name__)
ORDERS_FILE = os.path.join(os.path.dirname(__file__), "orders.txt")
VALID = ["B", "C", "D"]

robot_status = {"state": "IDLE", "current": "", "completed": 0, "log": [], "last_update": time.time()}

def read_orders():
    try:
        lines = open(ORDERS_FILE).readlines()
        return [l.strip().upper() for l in lines if l.strip().upper() in VALID]
    except:
        return []

def write_orders(orders):
    open(ORDERS_FILE, "w").write("\n".join(orders) + ("\n" if orders else ""))

def add_log(msg):
    t = time.strftime("%H:%M:%S")
    robot_status["log"].insert(0, {"time": t, "msg": msg})
    robot_status["log"] = robot_status["log"][:50]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    orders = read_orders()
    counts = {k: orders.count(k) for k in VALID}
    return jsonify({
        "orders": orders,
        "counts": counts,
        "state": robot_status["state"],
        "current": robot_status["current"],
        "completed": robot_status["completed"],
        "log": robot_status["log"],
        "online": (time.time() - robot_status["last_update"]) < 10,
    })

@app.route("/api/add", methods=["POST"])
def add():
    dest = request.get_json().get("dest", "").upper()
    if dest not in VALID:
        return jsonify({"error": "Noto'g'ri"}), 400
    orders = read_orders()
    orders.append(dest)
    write_orders(orders)
    add_log(f"{dest} zonaga buyurtma qo'shildi")
    return jsonify({"ok": True})

@app.route("/api/delete", methods=["POST"])
def delete():
    idx = request.get_json().get("index", -1)
    orders = read_orders()
    if 0 <= idx < len(orders):
        removed = orders.pop(idx)
        write_orders(orders)
        add_log(f"#{idx+1} buyurtma ({removed}) bekor qilindi")
        return jsonify({"ok": True})
    return jsonify({"error": "Topilmadi"}), 404

@app.route("/api/clear", methods=["POST"])
def clear():
    write_orders([])
    add_log("Barcha buyurtmalar o'chirildi")
    return jsonify({"ok": True})

@app.route("/api/robot_update", methods=["POST"])
def robot_update():
    data = request.get_json()
    robot_status["last_update"] = time.time()
    for k in ["state", "current", "completed"]:
        if k in data: robot_status[k] = data[k]
    if "log" in data: add_log(data["log"])
    return jsonify({"ok": True})

if __name__ == "__main__":
    if not os.path.exists(ORDERS_FILE):
        open(ORDERS_FILE, "w").close()
    print("http://localhost:5000")
    app.run(debug=True, port=5000)