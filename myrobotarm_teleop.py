from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import threading
import time

import numpy as np

try:
    import pygame
except ImportError:  # pragma: no cover - optional dependency
    pygame = None

try:
    from lerobot.teleoperators.teleoperator import Teleoperator
    from lerobot.teleoperators.config import TeleoperatorConfig
except ImportError:  # pragma: no cover - runtime fallback for local use
    raise RuntimeError("lerobot is required for class definitions. - " + ImportError.__str__())

@TeleoperatorConfig.register_subclass("lerobot_teleoperator_myrobotarm_teleop")
@dataclass
class MyRobotTeleConfig(TeleoperatorConfig):
    """Configuration for a joystick-controlled robot arm teleoperator."""
    #not used
    port: str = "channels=16"
    baud_rate: int = 115200
    timeout: float = 1.0

    #mandatory parameters for myrobotarm teleop
    num_joints: int = 6    #this is the number of joints in the robot arm, which is 6 for the myrobotarm
    deadzone: float = 0.25
    sensitivity: float = 8.0
    update_hz: float = 50.0


class MyRobotTele(Teleoperator):
    config_class = MyRobotTeleConfig
    name = "lerobot_teleoperator_myrobotarm_teleop"

    def __init__(self, config: MyRobotTeleConfig):
        super().__init__(config)
        self.port = config.port
        self.baud_rate = config.baud_rate
        self.timeout = config.timeout
        self.num_joints = config.num_joints
        self.deadzone = config.deadzone
        self.sensitivity = config.sensitivity
        self.update_hz = config.update_hz
        self.config = config

        self.joy = None
        self.kit = None
        self.servos = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._mutex = threading.Lock()
        # set initial angles for all 6 joints; keep it the same as in myrobotarm.py!!
        self._angles = np.array([102.0, 160.0, 150.0, 90.0, 50.0, 30.0], dtype=np.float32)
        self._calibrated = False

    # @property
    # #def action_features(self) -> dict:
    #     return {
    #         "action": (self.num_joints,),
    #     }

    # def get_action(self) -> dict[str, Any]:
    #     """Return the latest servo angles as the action vector."""
    #     with self._mutex:
    #         angles = self._angles.copy()
    #     return {"action": angles}

    @property
    def action_features(self) -> dict[str, type]:
        return {f"joint_{i+1}.pos": float for i in range(self.num_joints)}

    def get_action(self) -> dict[str, Any]:
        """Return the latest servo angles as scalar values."""
        with self._mutex:
            angles = self._angles.copy()
        return {f"joint_{i+1}.pos": float(angle) for i, angle in enumerate(angles)}    

    @property
    def feedback_features(self) -> dict[str, type]:
        return {}

    @property
    def is_connected(self) -> bool:
        return self.joy is not None

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def connect(self) -> None:
        """Connect to the joystick and start the background polling thread."""
        if pygame is None:
            raise RuntimeError("pygame is required for joystick teleop")

        print("Connecting to Joystick...")
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError("No joystick detected")

        self.joy = pygame.joystick.Joystick(0)
        self.joy.init()
        
        # #no need get Servo as there's no leader arm in this case.
        # if ServoKit is not None:
        #     self.kit = ServoKit(channels=16)
        #     self.servos = [self.kit.servo[index] for index in range(6)]
        #     #self._apply_to_servos() 

        self._calibrated = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._joystick_loop, daemon=True)
        self._thread.start()

        print("Connected to: ",self.joy.get_name())

    def calibrate(self) -> None:
        self._calibrated = True

    def configure(self) -> None:
        pass

    def send_feedback(self, feedback: dict[str, float]) -> None:
        pass

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=0.5)
        self._thread = None
        self.joy = None

    def _joystick_loop(self) -> None:
        while not self._stop_event.is_set():
            if self.joy is None:
                print ("Joystick not connected. Waiting for connection...")
                time.sleep(0.01)
                continue

            pygame.event.pump()

            lx = self._normalize_axis(self.joy.get_axis(0))
            ly = self._normalize_axis(self.joy.get_axis(1))
            rx = self._normalize_axis(self.joy.get_axis(3))
            ry = self._normalize_axis(self.joy.get_axis(2))

            with self._mutex:
                self._angles[0] = self._clamp(self._angles[0] + (-1.0*lx * self.sensitivity), 0.0, 180.0) #left joystick left-right controls base rotation
                self._angles[1] = self._clamp(self._angles[1] - (ly * self.sensitivity), 0.0, 180.0) #left joystick up-down controls shoulder up-down
                self._angles[2] = self._clamp(self._angles[2] + (rx * self.sensitivity), 0.0, 180.0) #right joystick up-down controls elbow up-down
                self._angles[3] = self._clamp(self._angles[3] - (ry * self.sensitivity), 0.0, 180.0) #right joystick left-right controls wrist rotation

                if self.joy.get_button(6): #button LT, wrist up
                    self._angles[4] = self._clamp(self._angles[4] + self.sensitivity, 0.0, 180.0)
                if self.joy.get_button(7): #button RT, wrist down
                    self._angles[4] = self._clamp(self._angles[4] - self.sensitivity, 0.0, 180.0)
                if self.joy.get_axis(5) > 0.5: #button LB, gripper open
                    self._angles[5] = self._clamp(self._angles[5] + self.sensitivity, 0.0, 180.0)
                if self.joy.get_axis(4) > 0.5: #button RB, gripper close
                    self._angles[5] = self._clamp(self._angles[5] - self.sensitivity, 0.0, 180.0)

                if self.joy.get_button(0): #button A
                    self.sensitivity = self.sensitivity + 1
                if self.joy.get_button(3): #button X
                    self.sensitivity = self.sensitivity - 1
                if self.joy.get_button(1): #button B
                    self._angles[0] = 102.0
                    self._angles[1] = 180.0
                    self._angles[2] = 180.0
                    self._angles[3] = 90.0
                    self._angles[4] = 50.0
                    self._angles[5] = 30.0
                    self.sensitivity = self.config.sensitivity

            #how often to update the angles from the joystick
            time.sleep(1.0 / self.update_hz)

    def _normalize_axis(self, value: float) -> float:
        if abs(value) < self.deadzone:
            return 0.0
        return float(np.clip(value, -1.0, 1.0))

    #not in use as there's no leader arm in this case.
    def _apply_to_servos(self) -> None:
        if self.kit is None:
            return

        for index, angle in enumerate(self._angles[: len(self.servos)]):
            try:
                self.servos[index].angle = float(angle)
            except Exception:
                continue

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    