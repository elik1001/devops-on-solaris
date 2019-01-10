#!/bin/bash

case $1 in
'start')
    svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: "running"

    /usr/bin/rsync -av --delete --progress /apps1/ /apps1_clone >> /var/tmp/rsync_status.log 2>&1 &
    rtc=$?
    if [ "${rtc}" != "0" ] ; then
        svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: \"error: ${rtc}\"
        exit ${rtc}
    fi
    ;;
'update')
    if [[ -z `pgrep rsync` ]] ; then
        if [[ -z `svccfg -s svc:/application/apps1_mount:apps1sync listprop config/sync_stat|grep error` ]] ; then
            echo 'Rsync completed successfully.'
            svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: "completed"
        else
            echo 'Rsync completed with errors.'
        fi
    else
        echo 'Rsync is still running'
    fi
    ;;
'stop')
        pkill rsync
        svccfg -s svc:/application/apps1_mount:apps1sync setprop config/sync_stat = astring: "initial"
    ;;
esac
