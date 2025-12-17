#!/bin/bash

#compile the services
gcc test-backlog128.c -o backlog128
gcc test-backlog64.c -o backlog64
gcc test-backlog32.c -o backlog32

gcc test-not_backlog128.c -o not_backlog128
gcc test-not_backlog64.c -o not_backlog64
gcc test-not_backlog32.c -o not_backlog32

#run the services
./backlog128&
./backlog64&
./backlog32&

./not_backlog128&
./not_backlog64&
./not_backlog32&


echo "Services up and running"



