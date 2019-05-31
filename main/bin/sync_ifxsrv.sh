#!/bin/bash

# >/var/tmp/ifx_rsync_status.log
case $1 in
'start')
    for mnt in /ifxsrv /ifxsrv_clone ;do
      count=0
      while [ "${count}" -lt 5 ] ; do
        mount=`/usr/bin/df -h "${mnt}" 2>&- |grep "${mnt}" |awk '{print $6}'`
        if [ "${mount}" = "" ] ; then
          echo "$mnt not available yet." >> /var/tmp/mount_log.out
          sleep 1
          if [ "${count}" = "4" ] ; then
            echo "$mnt not available after 5 trys, giving up!." >> /var/tmp/mount_log.out
            svccfg -s svc:/application/informix_mount:ifxsync setprop config/sync_stat = astring: \"error: ${mnt} not available after 5 trys, giving up.\"
            exit 1
          fi
        else
          echo "$mnt available continuing." >> /var/tmp/mount_log.out
          break
        fi
      count=`expr $count + 1`
      done
    done

    svccfg -s svc:/application/informix_mount:ifxsync setprop config/sync_stat = astring: "running"

    /usr/bin/rsync -av --delete --progress /ifxsrv/ /ifxsrv_clone >> /var/tmp/ifx_rsync_status.log 2>&1 &
    rtc=$?
    sleep 2
    if [ "${rtc}" != "0" ] ; then
        svccfg -s svc:/application/informix_mount:ifxsync setprop config/sync_stat = astring: \"error: ${rtc}\"
        exit ${rtc}
    fi
    ;;
'update')
    if [[ -z `pgrep rsync` ]] ; then
        if [[ -z `svccfg -s svc:/application/informix_mount:ifxsync listprop config/sync_stat|grep error` ]] ; then
            echo 'Rsync completed successfully.'
            svccfg -s svc:/application/informix_mount:ifxsync setprop config/sync_stat = astring: "completed"
        else
            echo 'Rsync completed with errors.'
        fi
    else
        echo 'Rsync is still running'
    fi
    ;;
'stop')
        pkill rsync
        svccfg -s svc:/application/informix_mount:ifxsync setprop config/sync_stat = astring: "initial"
    ;;
esac

