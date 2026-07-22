from adafruit_servokit import ServoKit
import pygame
import time

kit = ServoKit(channels=16)
pygame.init()
pygame.joystick.init()
print("Controllers found:", pygame.joystick.get_count())
joy = pygame.joystick.Joystick(0)
joy.init()
print(joy.get_name())
print("Use joysticks to move. Press B to quit. Press A to increase sensitivity. Press X to decrease sensitivity.")

servo1 = kit.servo[0]
servo2 = kit.servo[1]
servo3 = kit.servo[2]
servo4 = kit.servo[3]
servo5 = kit.servo[4]
servo6 = kit.servo[5]
servo1.angle = 90  
servo2.angle = 180
servo3.angle = 140
servo4.angle = 90
servo5.angle = 90
servo6.angle = 0
sensitivity = 8

try:
    while True:
        pygame.event.pump()

        lx = joy.get_axis(0)
        ly = joy.get_axis(1)            
        rx = joy.get_axis(3)
        ry = joy.get_axis(2)


        deadzone = 0.25
        diagonal1 = 0.6
        diagonal2 = 0.6

        alx=abs(lx)
        aly=abs(ly)
        arx=abs(rx)
        ary=abs(ry)
        

        if alx < deadzone:
            lx=0
        if aly < deadzone:
            ly=0
        if arx < deadzone:
            rx=0
        if ary < deadzone:
            ry=0

        ax=abs(lx)
        ay=abs(ly)
        arx=abs(rx)
        ary=abs(ry)

        diagonal1 = (alx>deadzone and aly>deadzone and min(alx,aly)/max(alx,aly)>diagonal1)
        diagonal2 = (arx>deadzone and ary>deadzone and min(arx,ary)/max(arx,ary)>diagonal2)

        if not diagonal1:
            if ax>ay:
                ly=0
            else:
                lx=0

        if not diagonal2:
            if arx>ary:
                ry=0
            else:
                rx=0

        if -1<=lx<=-0.2:
            servo1.angle = min(servo1.angle + sensitivity, 180)
        elif 0.2<=lx<=1:
            servo1.angle = max(servo1.angle - sensitivity , 0)


        if -1<=ly<=-0.2:
            servo2.angle = min(servo2.angle + sensitivity, 180)
        elif 0.2<=ly<=1:
            servo2.angle = max(servo2.angle - sensitivity , 0)

        if -1<=rx<=-0.2:
            servo3.angle = max(servo3.angle - sensitivity , 0)
        elif 0.2<=rx<=1:
            servo3.angle = min(servo3.angle + sensitivity, 180)
            


        if -1<=ry<=-0.2:
            servo4.angle = max(servo4.angle - sensitivity , 0)
        elif 0.2<=ry<=1:
            servo4.angle = min(servo4.angle + sensitivity, 180)
            

        if joy.get_button(0):
            sensitivity = sensitivity + 1
        if joy.get_button(3):
            sensitivity = sensitivity - 1
        if joy.get_button(1):
            break

        if joy.get_button(6):
            servo6.angle = min(servo6.angle + sensitivity, 180)
        if joy.get_button(7):
            servo6.angle = max(servo6.angle - sensitivity , 0)

        if joy.get_axis(5)>0.5:
            servo5.angle = min(servo5.angle + sensitivity, 180)
        if joy.get_axis(4)>0.5:
            servo5.angle = max(servo5.angle - sensitivity , 0)

        
        time.sleep(0.05)



finally:
    servo1.angle = 90  
    servo2.angle = 180
    servo3.angle = 140
    servo4.angle = 90
    servo5.angle = 90
    servo6.angle = 0