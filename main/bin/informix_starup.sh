#!/bin/bash


case $1 in
'start')
    /usr/ifxsrv/ifmx_dba/bin/ifx_init.ksh
    rtc=$?
    if [ "${rtc}" != "0" ] ; then
        exit ${rtc}
    else
        /sbin/svcadm disable svc:/application/db_startup:ifxinit
        sleep 1
        /sbin/svcadm enable svc:/application/db_startup:ifxsrvr
        exit 0
    fi
    ;;
'stop')
        /usr/bin/su - informix -c "/usr/ifxsrv/bin/onmode -ky" >>/var/tmp/informix.out 2>&1
        sleep 3
        /usr/bin/su - informix -c "/usr/ifxsrv/bin/onclean -ky" >>/var/tmp/onclean.out 2>&1
        sleep 10
        
    ;;
'port') 
        if  ! grep 1708 /usr/ifxsrv/etc/sqlhosts ; then
            echo "ext     onsoctcp     `ipadm show-addr -p -o addr net0/v4| cut -d\/ -f1`    1708" >>/usr/ifxsrv/etc/sqlhosts
        else
           if  ! grep 1708 /usr/ifxsrv/etc/sqlhosts | grep -w `ipadm show-addr -p -o addr net0/v4| cut -d\/ -f1`;then
               /usr/gnu/bin/sed -i "s/ext.*1708/ext     onsoctcp     `ipadm show-addr -p -o addr net0/v4| cut -d\/ -f1`    1708/" /usr/ifxsrv/etc/sqlhosts
           fi
        fi
        exit $?
    ;;
'*') echo "$0 usage [start|stop|port]"
    ;;
esac
