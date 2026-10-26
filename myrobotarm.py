import time
import numpy as np
#import serial
from adafruit_servokit import ServoKit
from lerobot.robots.robot import Robot
from lerobot.robots.config import RobotConfig
from lerobot.processor import RobotObservation, RobotAction
from lerobot.cameras.opencv import OpenCVCamera, OpenCVCameraConfig
from lerobot.cameras import CameraConfig,make_cameras_from_configs
from dataclasses import dataclass, field
from typing import Any

@RobotConfig.register_subclass("lerobot_robot_myrobotarm")
@dataclass
class MyRobotConfig(RobotConfig):
    """Configuration for ??-controlled robot."""
    #port: str = "/dev/ttyUSB0" no use
    port: str = "channels=16"
    baud_rate: int = 115200
    timeout: float = 1.0
    num_joints: int = 6
    #cameras: dict[str, OpenCVCameraConfig] | None = None
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

class MyRobot(Robot):
    """Robot controlled via PWM communication."""
    
    name = "lerobot_robot_myrobotarm"
    config_class = MyRobotConfig
    
    def __init__(self, config: MyRobotConfig):
        super().__init__(config)
        self.port = config.port
        self.baud_rate = config.baud_rate
        self.timeout = config.timeout
        self.num_joints = config.num_joints
        self.config=config
        
        self.robot_connection = None
        
        self.cameras = {}
        if config.cameras is not None:
            self.cameras = make_cameras_from_configs(config.cameras)        
        # Initialize cameras if configured
        # if config.cameras:
        #     for name, cam_config in config.cameras.items():
        #         self.cameras[name] = OpenCVCamera(cam_config)
    
    @property
    def _motors_ft(self) -> dict[str, type]:
        return {f"joint_{i+1}.pos": float for i in range(self.num_joints)}
    
    @property
    def _cameras_ft(self) -> dict[str, tuple]:
        return {
            name: (camera.height, camera.width, 3)
            for name, camera in self.cameras.items()
        }

    @property
    def observation_features(self) -> dict:
        features = {**self._motors_ft, **self._cameras_ft}
        return features
    
    @property
    def action_features(self) -> dict[str, type]:
        #return {f"joint_{i+1}": float for i in range(self.num_joints)}
        return self._motors_ft
    
    @property
    def is_connected(self) -> bool:
        return self.robot_connection is not None and all(
            camera.is_connected and camera.thread is not None and camera.thread.is_alive()
            for camera in self.cameras.values()
        )
    
    def connect(self) -> None:
        """Connect to robot via ?? port."""
        print(f"Connecting to robot on {self.port}...")
        
        try:
            self.robot_connection =ServoKit(channels=16)
            self.servo1 = self.robot_connection.servo[0] #base, joy1 left-right
            self.servo2 = self.robot_connection.servo[1] #shoulder, joy1 up-down
            self.servo3 = self.robot_connection.servo[2] #elbow, joy2 up-down
            self.servo4 = self.robot_connection.servo[3] #wrist-turn, joy2 left-right
            self.servo5 = self.robot_connection.servo[4] #griper-open/close, button LT-RT
            self.servo6 = self.robot_connection.servo[5] #wrist-up/down button LB-RB
                        
            # Wait for robot to initialize
            time.sleep(2)
            
            # Send initialization command
            self._send_command("INIT")

            # Connect cameras
            for name, camera in self.cameras.items():
                camera.connect()
                print(f"Camera '{name}' connected.")

            print("Robot connection established.")
            print("You can now use joysticks to teleoperate the robot.")

        except Exception as exc:
            # A camera may have opened before a later camera failed. Clean up
            # every partially initialized device and propagate the original
            # error so LeRobot does not continue with a dead camera thread.
            for camera in self.cameras.values():
                if camera.is_connected or camera.thread is not None:
                    try:
                        camera.disconnect()
                    except Exception:
                        pass

            if self.robot_connection is not None:
                try:
                    self._send_command("STOP")
                except Exception:
                    pass
                self.robot_connection = None

            raise RuntimeError(f"Failed to connect MyRobot: {exc}") from exc
    
    def disconnect(self) -> None:
        """Disconnect from robot."""
        if self.robot_connection is not None:
            self._send_command("STOP")
            self.servo1 = None
            self.servo2 = None
            self.servo3 = None
            self.servo4 = None
            self.servo5 = None
            self.servo6 = None
            self.robot_connection=None
            print("Robot connection closed.")
        
        # Disconnect cameras
        for camera in self.cameras.values():
            if camera.is_connected or camera.thread is not None:
                camera.disconnect()
    
    def get_observation(self) -> dict[str, Any]:
        """Read current state and images."""
        if not self.is_connected:
            raise RuntimeError("Robot not connected")
        
        obs_dict = {}
        # Read joint positions
        response = self._read_response()
        joint_positions = np.array([float(x) for x in response.split(",")])        
        for i, angle in enumerate(joint_positions[:6]):  # 6 angles
            obs_dict[f"joint_{i+1}.pos"] = angle
        
        # Capture images from all cameras
        for cam_key, cam in self.cameras.items():
            #start = time.perf_counter()
            obs_dict[cam_key] = cam.async_read()
            #dt_ms = (time.perf_counter() - start) * 1e3
            #logger.debug(f"{self} read {cam_key}: {dt_ms:.1f}ms")
        
        return obs_dict
    
    def send_action(self, action: RobotAction) -> None:
        """Send action command to robot."""
        if not self.is_connected:
            raise RuntimeError("Robot not connected")
        
        # Extract action values from dict
        #action_values = action.get("action", [])
        action_values = [
            action[f"joint_{i+1}.pos"]
            for i in range(self.num_joints)
        ]
        #print(f"Sending action: {action_values}")
        #Sending action: [72.84765625, 27.321044921875, 150.0, 90.0, 90.0, 30.0]
        action_str = ",".join([f"{x:.6f}" for x in action_values])
        command = f"SET_ACTION,{action_str}"
        
        self._send_command(command)
    
    def _send_command(self, command: str) -> None:
        """Send command over port."""
        if command == "INIT" or command == "STOP":
            # Set servos to initial positions, if you change here, need to change in teleop class too!!
            self.servo1.angle = 102.0
            self.servo2.angle = 180.0
            self.servo3.angle = 180.0
            self.servo4.angle = 90.0
            self.servo5.angle = 50.0
            self.servo6.angle = 30.0
        elif command.startswith("SET_ACTION"):
            parts = command.split(",")
            if parts[0] == "SET_ACTION" and len(parts) == self.num_joints + 1:
                angle_values = parts[1:]
            elif len(parts) == self.num_joints:
                angle_values = parts
            else:
                print(f"command {command} has an invalid angle count.")
                return

            try:
                angles = [float(angle) for angle in angle_values]
            except ValueError:
                print(f"command {command} contains non-numeric angles.")
                return

            if len(angles) != self.num_joints:
                print(f"command {command} must contain {self.num_joints} angles.")
                return

            self.servo1.angle = max(0.0, min(180.0, angles[0]))
            self.servo2.angle = max(0.0, min(180.0, angles[1]))
            self.servo3.angle = max(0.0, min(180.0, angles[2]))
            self.servo4.angle = max(0.0, min(180.0, angles[3]))
            self.servo5.angle = max(0.0, min(180.0, angles[4]))
            self.servo6.angle = max(0.0, min(180.0, angles[5]))
            #print(f"Applied angles from command: {angles}")
        else:
            print(f"command {command} not implemented.")
    
    def _read_response(self) -> str:
        """Read response from channels."""
        response = ",".join(map(str, [
            self.servo1.angle,
            self.servo2.angle,
            self.servo3.angle,
            self.servo4.angle,
            self.servo5.angle,
            self.servo6.angle
        ]))
        return response

    def calibrate(self) -> None:
        print ("calibrate() is called")
        pass

    def is_calibrated(self) -> bool:
        print ("is_calibrated() is called")
        return True
    
    def configure(self) -> None:
        print ("configure() is called")
        pass
