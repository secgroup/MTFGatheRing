#!/bin/bash
for ip in '10.235.76.41' '10.235.76.61' '10.235.76.177' '10.235.76.128'; do rsync -avz -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" --progress ~/repos/MTFGatheRing robot@${ip}:/home/robot/; done
