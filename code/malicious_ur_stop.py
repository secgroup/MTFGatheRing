#from rvor_functions import move_on_edge, rotate_over_node
from robot_functions import *
from requests import post
from json import loads

def main():
    # query the server to start
    print('connect to server')

    start()

    # after that each robot uses an own counter
    # in this way all the robot operations are synchronized
    begin_time = int(time())
    print('protocol begins')

    '''
    each clock follows these sequences of instruction:
        state = 'state name'
        set state function
        movement or rotation
        get states function
        sync clock function    
    '''

    # !!! make sure robot eyes are looking at left
    # if not, protocol does not work as expected
    init_eyes_motor(eyes_speed)

    if us.connected:
        us.mode = 'US-DIST-CM'

    if ir.connected:
        ir.mode = 'IR-PROX'

    # move untill no other robot block M
    while not set_node_info_m():
        cross_marker()
        move_on_edge()
        begin_time = wait_clock(begin_time) 

if __name__ == '__main__':
    main()
