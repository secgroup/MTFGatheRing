#from rvor_functions import move_on_edge, rotate_over_node
from robot_functions import *
from requests import post
from json import loads

def main():

    print('protocol begins')

    if us.connected:
        us.mode = 'US-DIST-CM'

    if ir.connected:
        ir.mode = 'IR-PROX'

    print('connect to server')

    # query the server to start
    start()

    # move untill no other robot block M
    while not set_node_info_m():
        sleep(1)
        cross_marker()
        move_on_edge(collision_distance=-1)
        # no need to sync, M is asynchronous

if __name__ == '__main__':
    main()
