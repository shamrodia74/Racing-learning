import os
import pygame
import copy
from math import cos, sin, sqrt, atan2, degrees
from numpy import sign, clip
from pygame.math import Vector2
from inputs import Inputs
"""
This is derived from https://github.com/spacejack/carphysics2d which simulates accurately car physics in 2D but is in Javascript
"""
sep = os.path.sep

class Car:
	def __init__(self, heading, position, load_image=True):

		self.heading = copy.deepcopy(heading) # angle in radians
		self.position = copy.deepcopy(position) # metres worlds coords
		self.velocity = Vector2() # m/s world coords
		self.velocity_c = Vector2() # m/s local coords, x is forward, y is sideways
		self.accel = Vector2() # acceleration in world coords
		self.accel_c = Vector2() # acceleration in local coords
		self.absVel = 0. # absolute velocity m/s
		self.yawRate = 0. # angular velocity in m/s
		self.steer = 0. # amount of steering input (-1.0 .. 1.0)
		self.steerAngle = 0. # actual front whell steer angle (-maxSteer .. maxSteer)

		self.inertia = 0.
		self.wheelBase = 0. # set from axle to CG lengths
		self.axleWeightRatioFront = 0. # % car weight on the front axle
		self.axleWeightRatioRear = 0. # % car weight on the read axle

		self.config = Config()
		self.setConfig()

		self.inputs = Inputs(init_pygame=load_image)
		if load_image:
			self.image = pygame.image.load(self.config.image_path).convert_alpha()
			self.image = pygame.transform.scale(self.image, (32, 16))

	def setConfig(self):
		self.inertia = self.config.mass * self.config.inertiaScale
		self.wheelBase = self.config.cgToFrontAxle + self.config.cgToRearAxle
		self.axleWeightRatioFront = self.config.cgToRearAxle / self.wheelBase # % car weight on front axle
		self.axleWeightRatioRear = self.config.cgToFrontAxle / self.wheelBase # % car weight on rear axle

	def getCarDict(self):
		car_stats = {"heading" : self.heading,
					 "position" : [self.position.x, self.position.y],
					 "velocity" : [self.velocity.x, self.velocity.y],
					 "acceleration" : [self.accel.x, self.accel.y],
					 "speed" : self.absVel,
					 "yawRate" : self.yawRate,
					 "steer" : self.steer,
					 "steerAngle" : self.steerAngle}
		return car_stats

	def updatePhysics(self, dt):

		cfg = self.config
		# Pre-calc heading vector
		sn = sin(self.heading)
		cs = cos(self.heading)

		# Get velocity in local car coords
		self.velocity_c.x = cs * self.velocity.x + sn * self.velocity.y
		self.velocity_c.y = cs * self.velocity.y - sn * self.velocity.x

		# Weight on axles based on centre of gravity and weight shift due to forward/reverse acceleration
		axleWeightFront = cfg.mass * (self.axleWeightRatioFront * cfg.gravity 
			- cfg.weightTransfer * self.accel_c.x * cfg.cgHeight / self.wheelBase)
		axleWeightRear = cfg.mass * (self.axleWeightRatioRear * cfg.gravity 
			+ cfg.weightTransfer * self.accel_c.x * cfg.cgHeight / self.wheelBase)

		# Resulting velocity of the wheels as result of the yaw rate of the car body
		# v = yawrate * r where r is distance from axle to CG and yawRate (angular velocity) in rad/s
		yawSpeedFront = cfg.cgToFrontAxle * self.yawRate
		yawSpeedRear = -cfg.cgToRearAxle * self.yawRate

		# Calculate slip angles for front and rear wheels (aka alpha)
		slipAngleFront = atan2(self.velocity_c.y + yawSpeedFront, abs(self.velocity_c.x)) - sign(self.velocity_c.x) * self.steerAngle
		slipAngleRear = atan2(self.velocity_c.y + yawSpeedRear, abs(self.velocity_c.x))

		tireGripFront = cfg.tireGrip
		tireGripRear = cfg.tireGrip * (1. - self.inputs.ebrake * (1. - cfg.lockGrip)) # reduce rear grip when ebrake on

		frictionForceFront_cy = clip(-cfg.cornerStiffnessFront * slipAngleFront, -tireGripFront, tireGripFront) * axleWeightFront
		frictionForceRear_cy = clip(-cfg.cornerStiffnessRear * slipAngleRear, -tireGripRear, tireGripRear) * axleWeightRear

		# Get amount of brake/throttle from our inputs
		brake = min(self.inputs.brake * cfg.brakeForce + self.inputs.ebrake * cfg.eBrakeForce, cfg.brakeForce)
		throttle = self.inputs.throttle * cfg.engineForce

		# Resulting force in local car coordinates
		# Implemented as RWD car only (Rear Wheel Drive)
		tractionForce_cx = throttle - brake * sign(self.velocity_c.x)
		tractionForce_cy = 0

		dragForce_cx = -cfg.rollResist * self.velocity_c.x - cfg.airResist * self.velocity_c.x * abs(self.velocity_c.x)
		dragForce_cy = -cfg.rollResist * self.velocity_c.y - cfg.airResist * self.velocity_c.y * abs(self.velocity_c.y)

		# total force in car coordinates
		totalForce_cx = dragForce_cx + tractionForce_cx
		totalForce_cy = dragForce_cy + tractionForce_cy + cos(self.steerAngle) * frictionForceFront_cy + frictionForceRear_cy

		# acceleration along car axes
		self.accel_c.x = totalForce_cx / cfg.mass # forward/reverse accel
		self.accel_c.y = totalForce_cy / cfg.mass # sideways accel

		# acceleration in world coordinates
		self.accel.x = cs * self.accel_c.x - sn * self.accel_c.y
		self.accel.y = sn * self.accel_c.x + cs * self.accel_c.y

		# update velocity
		self.velocity.x += self.accel.x * dt
		self.velocity.y += self.accel.y * dt

		self.absVel = self.velocity.length()

		# calculate rotationnal forces
		angularTorque = (frictionForceFront_cy + tractionForce_cy) * cfg.cgToFrontAxle - frictionForceRear_cy * cfg.cgToRearAxle

		# Sim gets unstable at very slow speed, so just stop the car
		if (abs(self.absVel) < 0.5 and throttle == 0.):
			self.velocity.x = 0.
			self.velocity.y = 0.
			self.absVel = 0.
			angularTorque = 0.
			self.yawRate = 0.

		angularAccel = angularTorque / self.inertia

		self.yawRate += angularAccel * dt
		self.heading += self.yawRate * dt

		# finally we can update position
		self.position.x += self.velocity.x * dt
		self.position.y += self.velocity.y * dt

	def applySmoothSteer(self, steerInput, dt):
		"""
		Smooth steering, apply maximum steering angle change velocity.
		Works only for analog input (values of steering between 0 and 1)
		"""
		steer = 0
		
		if abs(steerInput) > 0.001:

			steer = clip(steer + steerInput * dt * 2., -1., 1.) # -inp.right, inp.left

		else:
			if steer > 0:
				steer = max(steer - dt, 0)

			elif steer < 0:
				steer = min(steer + dt, 0)

		return steer

	def applySafeSteer(self, steerInput):
		"""
		Safe steering, limit the steering angle by the speed of the car.
		Prevents oversteer at expense of more understeer
		"""
		avel = min(self.absVel, 250.) # m/s
		steer = steerInput * (1. - (avel / 280.))
		return steer

	def update(self, dtms):
		dt = dtms / 1000. # delta T in seconds
		steerInput = self.inputs.right - self.inputs.left

		# Perform filtering on steering
		if self.config.smoothSteer:
			steer = self.applySmoothSteer(steerInput, dt)
		else:
			steer = steerInput

		if self.config.safeSteer:
			steer = self.applySafeSteer(steerInput)

		# Now set the actual steering angle
		self.steerAngle = steer * self.config.maxSteer

		# Now that the inputs have been filtered and we have our throttle,
		# brake and steering values, perform the car physics update

		self.updatePhysics(dt)

	def render(self):
		cfg = self.config
		surface = self.image
		
		return surface

	def getStats(self):
		statsLabel = ["Speed", "acceleration"]
		stats = [round(self.velocity_c.x * 3.6), round(self.accel_c.x)]
		text = ""
		for i in range(len(stats)):
			text += statsLabel[i] + ": "
			text += str(stats[i]) + " "
		return text

class Config:
	"""
	This class contains all the constants for the car and the world, for interesting results,
	some constants could be modified or randomized
	"""
	def __init__(self):
		self.gravity = 9.81 # m/s^2
		self.mass = 1000.0 # kg
		self.inertiaScale = 1.0 # multiply by mass for inertia
		self.halfWidth = 0.8 # centre to side of chassis (metres)
		self.cgToFront = 2.0 # centre of gravity to front of chassis (metres)
		self.cgToRear = 2.0 # centre of gravity to rear of chassis (metres)
		self.cgToFrontAxle = 1.25 # centre gravity to front axle
		self.cgToRearAxle = 1.25 # centre gravity to rear axle
		self.cgHeight = 0.55 # centre gravity height
		self.wheelRadius = 0.3 # includes tire and represents height of axle
		# self.wheelWidth = 0.2 # for render only
		self.tireGrip = 2. # How much grip tires have
		self.lockGrip = 0.9 # % of grip available when wheel is locked
		self.engineForce = 12000.
		self.brakeForce = 14000.
		self.eBrakeForce = self.brakeForce / 2.5
		self.weightTransfer = 0.2 # How much weight is transferred during acceleration/braking
		self.maxSteer = 3.14 # maximum steering angle in radians
		self.cornerStiffnessFront = 5.
		self.cornerStiffnessRear = 5.2
		self.airResist = 2.5 # air resistance ( * vel )
		self.rollResist = 8. # rolling resistance force ( * vel )
		self.safeSteer = False
		self.smoothSteer = True
		self.image_path = os.path.split(os.getcwd())[0] + sep +"resources"+ sep +"car.png"

def main():
	foo = Car(0.,0,0)

if __name__ == "__main__":
	main()