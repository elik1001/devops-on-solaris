#!/bin/bash

case $1 in 
'start')
    svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: "running"

    /usr/bin/rsync -av --delete --progress /apps1/ /apps1_clone >> /var/tmp/rsync_status.log 2>&1
    rtc=$?

    if [ "${rtc}" == "0" ] ; then
        svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: "completed"
    else
        svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: \"error: ${rtc}\"
    fi
    ;;
'stop')
        svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: "initial"
    ;;
esac

