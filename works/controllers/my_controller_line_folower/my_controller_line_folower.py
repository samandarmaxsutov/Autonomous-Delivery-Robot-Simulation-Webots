from controller import Robot
import os
import urllib.request
import json

ORDERS_FILE = os.path.join(os.path.dirname(__file__), "orders.txt")
VALID = ["B", "C", "D"]
DASHBOARD_URL = "http://localhost:5000/api/robot_update"


def notify_dashboard(state=None, current=None, completed=None, log=None):
    """Web dashboardga holat yuborish (xato bo'lsa jimgina o'tkazib yuboradi)"""
    try:
        payload = {}
        if state is not None:     payload["state"] = state
        if current is not None:   payload["current"] = current
        if completed is not None: payload["completed"] = completed
        if log is not None:       payload["log"] = log
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            DASHBOARD_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=0.3)
    except:
        pass  # Dashboard ishlamasa ham robot ishlayveradi


def follow_line(left_motor, right_motor,
                on_left, on_center, on_right,
                max_speed, clockwise):
    if on_center and not on_left and not on_right:
        left_motor.setVelocity(max_speed)
        right_motor.setVelocity(max_speed)
    elif on_left and not on_right:
        left_motor.setVelocity(-max_speed * 0.5)
        right_motor.setVelocity(max_speed)
    elif on_right and not on_left:
        left_motor.setVelocity(max_speed)
        right_motor.setVelocity(-max_speed * 0.5)
    elif on_left and on_right:
        left_motor.setVelocity(max_speed)
        right_motor.setVelocity(max_speed)
    else:
        if clockwise:
            left_motor.setVelocity(max_speed * 0.5)
            right_motor.setVelocity(-max_speed * 0.5)
        else:
            left_motor.setVelocity(-max_speed * 0.5)
            right_motor.setVelocity(max_speed * 0.5)


def read_next_order():
    try:
        with open(ORDERS_FILE, "r") as f:
            lines = [l.strip().upper() for l in f.readlines()]
        for line in lines:
            if line in VALID:
                return line
    except:
        pass
    return None


def complete_order(destination):
    try:
        with open(ORDERS_FILE, "r") as f:
            lines = f.readlines()
        new_lines = []
        removed = False
        for line in lines:
            if not removed and line.strip().upper() == destination:
                removed = True
                continue
            new_lines.append(line)
        with open(ORDERS_FILE, "w") as f:
            f.writelines(new_lines)
        remaining = len([l for l in new_lines if l.strip().upper() in VALID])
        print(f"[orders] '{destination}' bajarildi. Qolgan: {remaining} ta")
    except Exception as e:
        print(f"[orders] Xato: {e}")


def count_orders():
    try:
        with open(ORDERS_FILE, "r") as f:
            lines = [l.strip().upper() for l in f.readlines()]
        return len([l for l in lines if l in VALID])
    except:
        return 0


def run_robot(robot):
    time_step = 32
    max_speed = 4.0
    THRESHOLD = 500
    WAIT_TIME = 90

    left_motor  = robot.getDevice("left wheel motor")
    right_motor = robot.getDevice("right wheel motor")
    left_motor.setPosition(float('inf'))
    right_motor.setPosition(float('inf'))
    left_motor.setVelocity(0.0)
    right_motor.setVelocity(0.0)

    left_ir   = robot.getDevice("left_ir")
    center_ir = robot.getDevice("center_ir")
    right_ir  = robot.getDevice("right_ir")
    left_ir.enable(time_step)
    center_ir.enable(time_step)
    right_ir.enable(time_step)

    receiver = robot.getDevice("receiver")
    receiver.enable(time_step)

    STATE_IDLE    = "idle"
    STATE_TO_DEST = "going_to_dest"
    STATE_WAIT    = "waiting"
    STATE_TO_A    = "going_to_A"
    STATE_WAIT_A  = "waiting_at_A"

    state       = STATE_IDLE
    wait_count  = 0
    last_seen   = None
    destination = None
    completed   = 0

    print("=== DELIVERY ROBOT ===")
    print(f"orders.txt: {ORDERS_FILE}")
    print(f"Qolgan buyurtmalar: {count_orders()} ta")
    notify_dashboard(state="IDLE", current="", completed=0, log="Robot ishga tushdi")

    while robot.step(time_step) != -1:

        signal = None
        while receiver.getQueueLength() > 0:
            signal = receiver.getBytes().decode()
            receiver.nextPacket()

        l = left_ir.getValue()
        c = center_ir.getValue()
        r = right_ir.getValue()
        print(f"IR: L={l:.1f} C={c:.1f} R={r:.1f} | State: {state} | Signal: {signal}")
        on_left   = l > THRESHOLD
        on_center = c > THRESHOLD
        on_right  = r > THRESHOLD

        # ── IDLE — yangi buyurtma kutish ──
        if state == STATE_IDLE:
            left_motor.setVelocity(0.0)
            right_motor.setVelocity(0.0)
            next_order = read_next_order()
            if next_order:
                destination = next_order
                state       = STATE_TO_DEST
                last_seen   = None
                wait_count  = 0
                msg = f"Yangi buyurtma: A → {destination} | Qolgan: {count_orders()}"
                print(f"=== {msg} ===")
                notify_dashboard(state=STATE_TO_DEST, current=destination,
                                 completed=completed, log=msg)
            continue

        # ── A → manzil ──
        if state == STATE_TO_DEST:
            if signal == "e" and destination != "C":
                signal = None
            if signal == "f" and destination != "D":
                signal = None

            if signal == "e" and destination == "C" and last_seen != "e":
                last_seen = "e"
                print("[e] Chapga burilmoqda (C yo'li)...")
                for _ in range(15):
                    robot.step(time_step)
                    left_motor.setVelocity(max_speed)
                    right_motor.setVelocity(max_speed)
                for _ in range(25):
                    robot.step(time_step)
                    left_motor.setVelocity(-max_speed * 0.5)
                    right_motor.setVelocity(max_speed * 0.5)
                while receiver.getQueueLength() > 0:
                    receiver.getBytes()
                    receiver.nextPacket()
                signal = None
                continue

            if signal == "f" and destination == "D" and last_seen != "f":
                last_seen = "f"
                print("[f] Chapga burilmoqda (D yo'li)...")
                for _ in range(15):
                    robot.step(time_step)
                    left_motor.setVelocity(max_speed)
                    right_motor.setVelocity(max_speed)
                for _ in range(25):
                    robot.step(time_step)
                    left_motor.setVelocity(-max_speed * 0.5)
                    right_motor.setVelocity(max_speed * 0.5)
                while receiver.getQueueLength() > 0:
                    receiver.getBytes()
                    receiver.nextPacket()
                signal = None
                continue

            if signal == destination and last_seen != destination:
                last_seen  = destination
                wait_count = 0
                state      = STATE_WAIT
                left_motor.setVelocity(0)
                right_motor.setVelocity(0)
                msg = f"{destination} ga yetdik! Yuklanmoqda..."
                print(f"=== {msg} ===")
                notify_dashboard(state=STATE_WAIT, current=destination,
                                 completed=completed, log=msg)
                continue

            follow_line(left_motor, right_motor,
                        on_left, on_center, on_right,
                        max_speed, clockwise=False)

        # ── Manzilda kutish ──
        elif state == STATE_WAIT:
            wait_count += 1
            left_motor.setVelocity(0)
            right_motor.setVelocity(0)
            if wait_count >= WAIT_TIME:
                complete_order(destination)
                completed += 1
                state     = STATE_TO_A
                last_seen = None
                msg = f"{destination} bajarildi → A ga qaytilmoqda"
                print(f"=== {msg} ===")
                notify_dashboard(state=STATE_TO_A, current=destination,
                                 completed=completed, log=msg)

        # ── Manzil → A ──
        elif state == STATE_TO_A:
            if signal in ["e", "f"]:
                signal = None

            if signal == "A" and last_seen != "A":
                last_seen  = "A"
                wait_count = 0
                state      = STATE_WAIT_A
                left_motor.setVelocity(0)
                right_motor.setVelocity(0)
                msg = "A ga qaytdik!"
                print(f"=== {msg} ===")
                notify_dashboard(state=STATE_WAIT_A, current="",
                                 completed=completed, log=msg)
                continue

            follow_line(left_motor, right_motor,
                        on_left, on_center, on_right,
                        max_speed, clockwise=True)

        # ── A da kutish ──
        elif state == STATE_WAIT_A:
            wait_count += 1
            left_motor.setVelocity(0)
            right_motor.setVelocity(0)
            if wait_count >= WAIT_TIME:
                remaining = count_orders()
                state      = STATE_IDLE
                wait_count = 0
                if remaining > 0:
                    msg = f"Keyingi buyurtmaga o'tilmoqda... ({remaining} ta qoldi)"
                else:
                    msg = "Barcha buyurtmalar bajarildi! Yangi buyurtma kutilmoqda..."
                print(f"=== {msg} ===")
                notify_dashboard(state="IDLE", current="",
                                 completed=completed, log=msg)


if __name__ == "__main__":
    robot = Robot()
    run_robot(robot)