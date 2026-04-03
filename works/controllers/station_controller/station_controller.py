from controller import Robot

robot = Robot()
timestep = int(robot.getBasicTimeStep())

emitter = robot.getDevice("emitter")
name = robot.getName()
signal = name.split("_")[-1]

print(f"=== Stansiya {signal} ishga tushdi ===")

step = 0
while robot.step(timestep) != -1:
    emitter.send(signal.encode())
    step += 1
    # if step % 50 == 0:  # Har 50 qadamda bir marta print
    #     print(f"[{name}] '{signal}' signal yuborildi")