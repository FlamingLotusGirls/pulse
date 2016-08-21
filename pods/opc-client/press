#!/bin/bash
# vim:set ts=4 sw=4 ai et:

# Manually simulate button presses on the sculpture.

usage() { echo "Usage: $0 [-w]" 1>&2; exit 1; }

while getopts "w" o; do
    case "${o}" in
        w)
            WAIT="yes"
            ;;
        *)
            usage
            ;;
    esac
done

shift $((OPTIND-1))

#if ! test -d /var/run/soma
#then
#    echo "Directory /var/run/soma does not exist"
#    exit 1
#fi

echo "Ready"

BUTTON=/tmp/buttonA

while true
do
    read -s -n 1 i

    if test "$i" = "1" || test "$i" = "l" || test "$i" = "a"
    then
        BUTTON=/tmp/buttonA
    elif test "$i" = "0" || test "$i" = "r" || test "$i" = "b"
    then
        BUTTON=/tmp/buttonB
    elif test "$i" = "r"
    then
        echo "Restarting"
        sudo systemctl restart opc-client.service
        continue
    fi

    echo -n "$(date +%H:%M:%S)  Pressed $BUTTON  "
    touch $BUTTON

    if test "$WAIT" = "yes"
    then
        read -s -n 1 i
    else
        sleep 0.5
    fi

    echo "Released"
    rm -f $BUTTON
done
