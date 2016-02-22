from time import time, sleep
from ev3dev.auto import *
import socket

# motors
motor_r = LargeMotor(OUTPUT_D)
motor_l = LargeMotor(OUTPUT_A)
motor_m = MediumMotor(OUTPUT_B)

# sensors
color = ColorSensor()
touch = TouchSensor()
gyro = GyroSensor()
us = UltrasonicSensor()
ir = InfraredSensor()

# follow border setting
black_color_pct = 5
white_color_pct = 82 #80
mid_point = (black_color_pct + white_color_pct)/2

color_kp = 0.45

#explore_node_speed = -25
move_on_edge_speed = -33
cross_line_speed = -22
rotate_over_node_speed = -22

rotate_speed = -30

nbr_cols_sampled = 8

gathering_max_distance = 330 # mm
collision_avoidance_distance = 70 # mm

#eyes_rotation_degree = 140
#rotation_degree_same_direction = 140
#rotation_degree_diff_direction = 20

eyes_speed = 40

# syncronized clock time unit in seconds
sync_clock_time = 9

#serverMACAddress = '00:17:EC:03:17:C2' # bluetooth robot 3
#serverMACAddress = 'AC:7B:A1:A4:B8:7E' # bluetooth address my pc
serverMACAddress = '00:17:EC:F6:06:4B' # bluetooth robot 4
port = 3
server_socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
buffer_size = 32

def look():
    if us.connected:
        return us.value()

    if ir.connected:
        #return ir.value()
        # fake value, infrared is never used in protocol
        # use it only for robot that will became leader
        # because for this robot eyes are useless
        return 999

def can_I_move(clockwise_direction):
    print('query server to know if M is over next node')
    direction = int(clockwise_direction) # 1 if clockwise_direction is true, 0 otherwise
    # send to server the current direction, in byte
    server_socket.send( direction.to_bytes(1, byteorder='big') )
    # wait the response
    resp = server_socket.recv(buffer_size) # 00 or 01 in byte
    int_resp = int.from_bytes(resp, byteorder='big')
    return bool(int_resp)

def start_motor(motor, speed):
    #print('motor starts')
    motor.speed_regulation_enabled = 'off'
    motor.run_direct(duty_cycle_sp = speed)

def start_motors(speed):
    start_motor(motor_r, speed)
    start_motor(motor_l, speed)

def is_color_white(color_sampled):
    error_threshold = 10
    avg_color_sampled = sum(color_sampled)//nbr_cols_sampled
    return (white_color_pct - avg_color_sampled) <= error_threshold

# return true if color sampled is white or yellow
def is_not_color_black(color_sampled):
    error_threshold = 10
    avg_color_sampled = sum(color_sampled)//nbr_cols_sampled
    # it works because yellow color pct are greater than white color pct
    # and both are greater than black color pct
    return avg_color_sampled >= (white_color_pct - error_threshold)

def stop_motors():
    motor_r.stop()
    motor_l.stop()

def wait_clock(begin_time, nbr_clocks=1):

    last_time = begin_time
    while True:
        new_time = int(time())

        diff_time = new_time - begin_time

        if ( diff_time >= nbr_clocks*sync_clock_time ):
            print('\t\t' + str(diff_time) + ' seconds')
            print ("\t------------- clock time expired -------------\n")
            return new_time

        if ( (diff_time % 2) == 0 and last_time != new_time ):
            print('\t\t' + str(diff_time) + ' seconds')

        last_time = new_time


def is_special_node():
    color.mode = 'COL-COLOR'
    color_value = color.value()
    print('color is ' + str(color_value))
    return color_value == 4 # 4 is yellow color, see ev3dev doc

def rotate_counterclockwise(degree):
    # reset gyroscope
    gyro.mode = 'GYRO-RATE'
    gyro.mode = 'GYRO-ANG'

    start_motor(motor_r, rotate_speed)
    while True:
        if (gyro.value() <= -degree):
            stop_motors()
            break

def init_eyes_motor(speed):
    motor_m.reset()
    motor_m.speed_regulation_enabled = 'off'
    motor_m.duty_cycle_sp = speed

# use this function when ultra sound sensor us is in mode US-DIST-CM
# in this mode last digit is decimal, in practice the unit is mm, not cm
# blocking call!
def is_there_close_robot(rotation_degree, distance = gathering_max_distance):
    #init_eyes_motor(eyes_speed)

    close_robot_detected = False

    #us.mode = 'US-SI-CM'
    #sleep(0.3)
    us_value = look()
    sleep(0.2)

    print('ultrasound value is ' + str(us_value) + ' mm')
    if us_value <= distance:
        print('robot detected')
        close_robot_detected = True

    elif(rotation_degree != -1):
        # move eyes clockwise
        motor_m.run_to_abs_pos(position_sp = rotation_degree)
        # this time must be >= the time to perform a rotation
        # and then to look up, because it could take a while to focus the distance
        sleep(1.3)
        #print('real eyes rotation: ' + str(motor_m.position))

        us_value = look()
        sleep(0.2)

        print('ultrasound value is ' + str(us_value) + ' mm')
        if us_value <= distance:
            print('robot detected')
            close_robot_detected = True

        # move eyes counterclockwise to reset them in their original position
        motor_m.run_to_abs_pos(position_sp = 0)
        sleep(1)
        #print('real eyes rotation: ' + str(motor_m.position))

    return close_robot_detected

def left_correction():
    print('left correction')
    start_motor(motor_r, -15)
    start_motor(motor_l, 10)
    sleep(0.6)
    stop_motors()

def right_correction():
    print('right correction')
    start_motor(motor_r, 10)
    start_motor(motor_l, -15)
    sleep(0.6)
    stop_motors()

'''
Moving functions
'''
def follow_border(color_value, speed, line_ext):
    # with positive degree robot goes to right
    error = color_value - mid_point
    correction = color_kp*error

    right_speed = speed - correction
    left_speed = speed + correction

    if (not line_ext):
        right_speed = speed + correction
        left_speed = speed - correction

    motor_r.duty_cycle_sp = right_speed
    motor_l.duty_cycle_sp = left_speed
    
    return error

def cross_marker():
    print('cross marker area')
    color.mode = 'COL-COLOR'
    start_motors(cross_line_speed)
    while True:
        if color.value() == 1: # black color
            print('marker crossed\nstop')
            stop_motors()
            break

def rotate_over_node(collision_distance=-1, time_out=None):
    start_time = int(time())
    print('rotate over node')
    color.mode = 'COL-REFLECT'
    start_motors(rotate_over_node_speed)
    col_count = 0
    last_cols_sampled = [0]*nbr_cols_sampled


    if collision_distance != -1:
        print('move eyes.')
        motor_m.run_to_abs_pos(position_sp=30)
        sleep(0.5)
        #print('current eyes position = ' + str(motor_m.position))
        

    while True:
        elapsed_time = int(time()) - start_time

        color_sampled = color.value()
        color_error = follow_border(color_sampled, rotate_over_node_speed, False)
        last_cols_sampled[col_count] = color_sampled
        col_count = (col_count+1) % nbr_cols_sampled

        if ( (time_out != None) and (elapsed_time >= time_out) ):
            stop_motors()
            return False

        # stop when we found next marker
        if ( (elapsed_time >= 3) and is_not_color_black(last_cols_sampled)):
            stop_motors()
            left_correction()
            if collision_distance != -1:
                motor_m.run_to_abs_pos(position_sp=0)
                sleep(0.5)
            return False

        if collision_distance != -1:
            us_value = look()
            if ( us_value <= collision_distance ):
                stop_motors()
                print('a stopped robot has been detected at ' + str(us_value) + ' mm \nstop')
                # close eyes and reset them to their start position
                motor_m.run_to_abs_pos(position_sp=0)
                sleep(0.5) # time to move eyes
                #set_us_off()
                return True

def move_on_edge(collision_distance=collision_avoidance_distance, time_to_settle=4, time_out=None):
    start_time = int(time())
    print('move on edge')
    color.mode = 'COL-REFLECT'
    start_motors(move_on_edge_speed)
    col_count = 0
    last_cols_sampled = [0]*nbr_cols_sampled

    if collision_distance != -1:
        # robot must look in front of him, so that, when it is close to node,
        # it can detect if there is a stopped robot
        #init_eyes_motor(eyes_speed)
        #print('current eyes position = ' + str(motor_m.position))
        motor_m.run_to_abs_pos(position_sp=87)
        sleep(0.5)
        #print('current eyes position = ' + str(motor_m.position))

    while True:
        elapsed_time = int(time()) - start_time

        color_sampled = color.value()
        color_error = follow_border(color_sampled, move_on_edge_speed, True)
        last_cols_sampled[col_count] = color_sampled
        col_count = (col_count+1) % nbr_cols_sampled
              
        # stop when we found next marker
        # at the beginning robot slides
        # and so for a small elapsed time is not safe to check if it is outside of the black line
        if ( (elapsed_time >= time_to_settle) and is_not_color_black(last_cols_sampled) ):
            stop_motors()
            print('robot has reached the node')
            if collision_distance != -1:
                motor_m.run_to_abs_pos(position_sp=0)
                sleep(0.7)
            #set_us_off()
            return False            

        if collision_distance != -1:
            us_value = look()
            if ( us_value <= collision_distance ):
                stop_motors()
                print('a stopped robot has been detected at ' + str(us_value) + ' mm \nstop')
                # close eyes and reset them to their start position
                motor_m.run_to_abs_pos(position_sp=0)
                sleep(0.7) # time to move eyes
                #set_us_off()
                return True

        if ( (time_out != None) and (elapsed_time >= time_out) ):
            stop_motors()
            return False

def follower_init():
    print('became follower\n')
    cross_marker()
    rotate_over_node()
    cross_marker()
    move_on_edge()

def is_leader_moving():
    print('check if leader is moving')
    max_nbr_checks = 2

    check_done = 0
    motor_m.run_to_abs_pos(position_sp = 90)
    while check_done < max_nbr_checks:
        check_done += 1
        print('check nbr ' + str(check_done))
        # wait to complete eyes movement
        # but also to allow leader to increase the distance, if it is moving
        sleep(1.5)
        robot_detected = is_there_close_robot(-1, distance = collision_avoidance_distance)

        if not robot_detected:
            print('leader goes on, follow it')
            motor_m.run_to_abs_pos(position_sp = 0)
            # if leader is moving the first follower exits the while after one check
            # then it starts move
            # a possible second follower exits after two checks
            return True

    # two checks have been performed but the front robot is still stopped
    motor_m.run_to_abs_pos(position_sp = 0)
    sleep(0.8) # while eyes moving
    print('leader is stopped')
    return False

def enter_node_CW():
    print('enters the node')
    # check if another robot is already arrived in CW direction
    motor_m.run_to_abs_pos(position_sp = 40)
    sleep(2)
    robot_detected = is_there_close_robot(-1, distance = 120)

    # if no, move in the middle of the node arc
    if not robot_detected:
        cross_marker()
        rotate_over_node(time_out=4)

    #motor_m.run_to_abs_pos(position_sp = 0)
    #sleep(0.5)
