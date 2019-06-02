<h4>Securing the configuration manager system</h4>

Below is an example how to configure/secure a system were the devops_manager application is running on.

The application will only run as user <i>confmgr</i>.

Create a user confmgr in /etc/passwd, etc.., then add the below lines to /etc/user_attr
<pre>
confmgr::::auths=*;profiles=Primary Administrator,System Administrator,Zone Cold Migration,Zone Migration,Zone Configuration,Zone Security,All;defaultpriv=all;lock_after_retries=no
</pre>

<i>Note:</i> Non of our developers can login as user <i>confmgr</i>, they login by using their own login to the devops configuration manager system.

When they login they get a menu which will look something like the below.
In the below example we have two groups of users, an <i>admin</i>, and a regular <i>user(developer)</i> (you can setup many types of users - as many as you needed).

The <i>admin</i> menu looks like so.
<pre>
    *******************************************************************
                        Please Enter Your Choice
    *******************************************************************
    1) Create New Zone       2) List Your Zones       3) List All Zones

    4) Refresh Database      5) Refresh Applicati     6) Delete Zone

    7) Update DB Version     8) Admin Shell

                             Q) Quit
   ____________________________________________________________________
    Enter Choice:
</pre>

The <i>regular user</i> menu looks like so.
<pre>
    *******************************************************************
                        Please Enter Your Choice
    *******************************************************************
    1) Create New Zone       2) List Your Zones       3) Refresh Database

    4) Refresh Applicati     5) Delete Zone

                             Q) Quit
   ____________________________________________________________________
    Enter Choice:
</pre>

In <i>/etc/profile</i> we append the below lines.

if [ "${LOGNAME}" != "root" \
   -a "${LOGNAME}" != "confmgr" ] ; then
    exec /export/home/confmgr/multi_choice 0
fi

Below is how the <i>multi_choice</i> application looks like looks like, you place that in the confmgr home, typically in /export/home/confmgr.
<pre>
#!/bin/bash

trap "" 2 3
window=$1

menu_list_dir="/export/home/confmgr"
menu_access=`grep ^$LOGNAME: ${menu_list_dir}/access.db|awk -F\: '{print $2}'`
while [ "${num}" = "" ]; do

clear
echo ""
echo "    *******************************************************************
                        Please Enter Your Choice
    *******************************************************************"

grep "^${window}" "${menu_list_dir}/menu_list_${menu_access}" |awk -F\, '{print $2}' |pr -3 -a -n\) -d -t -w76
echo ""
echo "                             Q) Quit"

        if [ "${repeat}" = 1 ] ; then
echo "    *******************************************************************
    >>>>>>>>>>  SORRY, you did not enter a proper Selction  <<<<<<<<<<<
    *******************************************************************"
        fi
echo  "   ____________________________________________________________________"
/usr/gnu/bin/echo -n  "    Enter Choice: "
read num
count=1
if [ "${num}" = Q ] || [ "${num}" = q ] ;then
   exit 0
fi
flag="Y"
   while [ "${flag}" = "Y" ]
        do
     if [ "${num}" = "" ] ; then
      flag="N"
     fi
     if [ "${num}" != "" ] ; then
getlinenum=`grep "^${window}" ${menu_list_dir}/menu_list_${menu_access} |wc -l |awk '{print $1}'`
if [ "${num}" -gt "${getlinenum}" ] || [ "${num}" -lt 1 ] || [ "${num}" = "" ] ; then
repeat=1; flag="N"; num=""
        else
numresult0=`grep "^${window}" ${menu_list_dir}/menu_list_${menu_access} | head -${num} | tail -1 |awk -F\, '{print $3}'`
flag="N"
     fi
fi
   done
done

eval $numresult0
echo "\nHit enter to continue."
read junk
clear
exec /export/home/confmgr/multi_choice 0
</pre>

As you can see the <i>menu_access</i> variable will get set to the users access in <i>access.db</i>. i.e. it will call <i>/export/home/confmgr/menu_list_[10|5]</i> (based on how defined in access.db).

Next, you will have to create the <i>menu_list_10</i> and <i>menu_list_5</i> (or whatever your user/admin is mapped to).
An example of an <i>admin menu_list</i> is below.
<pre>
0, Create New Zone, sudo -u confmgr devops_manager.py -u $LOGNAME -p -i
0, List Your Zones, sudo -u confmgr devops_manager.py -u $LOGNAME -p -l
0, List All Zones, sudo -u confmgr devops_manager.py -u $LOGNAME -p -l det -a
0, Refresh Database, sudo -u confmgr devops_manager.py -u $LOGNAME -p -r db -i
0, Refresh Application Code, sudo -u confmgr devops_manager.py -u $LOGNAME -p -r app -i
0, Delete Zone, sudo -u confmgr devops_manager.py -u $LOGNAME -p -d -i
0, Update DB Version, sudo -u confmgr devops_manager.py -n -u $LOGNAME -p
0, Admin Shell, /bin/bash
</pre>

An example of a <i>regular user</i> menu
<pre>
0, Create New Zone, sudo -u confmgr devops_manager.py -u $LOGNAME -p -i
0, List Your Zones, sudo -u confmgr devops_manager.py -u $LOGNAME -p -l
0, Refresh Database, sudo -u confmgr devops_manager.py -u $LOGNAME -p -r db -i
0, Refresh Application Code, sudo -u confmgr devops_manager.py -u $LOGNAME -p -r app -i
0, Delete Zone, sudo -u confmgr devops_manager.py -u $LOGNAME -p -d -i
</pre>

The menu list is what options the <i>user / developer</i> will get when logging in to the system.

Of course the <i>devops_manager.py</i> application has many more options, but this simplifies usage for most users / developers / used cases using the application.

One last configuration is sudo. we need to configure <i>sudo</i> for all developers logging in to this system.

In our case we ware using LDAP, but you can use your local /etc/suders, will work as well.
The below example is what was appended to LDAP.
<pre>
dn: cn=confmgr,ou=SUDOers,o=domain.com,dc=domain,dc=com
sudoOption: !authenticate
sudoHost: confmgr
sudoHost: dc1-confmgr1
sudoCommand: /export/home/confmgr/devops_manager.py
cn: confmgr
sudoRunAs: confmgr
objectClass: top
objectClass: sudoRole
sudoUser: usera
sudoUser: userb
sudoUser: userc
</pre>

<i>Note:</i> Make sure the devops_config.ini is owned by <i>confmgr</i> user and only confmgr user can read it(as it contains passwords).

An example of file permissions
<pre>
-rw-r--r--   1 root     confmgr      191 May 31 09:19 access.db
drwxr-xr-x   2 confmgr  confmgr        5 Feb  4 13:48 bin
drwxr-xr-x   2 confmgr  confmgr       12 Feb  4 13:48 conf
-rw-r--r--   1 confmgr  confmgr        1 May 16 10:05 db_version.ini
-rw-r-----   1 confmgr  confmgr     5593 May 30 17:10 devops_config.ini
-rwx--x---   1 root     confmgr    91887 May 30 17:12 devops_manager.py
lrwxrwxrwx   1 root     root          20 May 31 09:17 menu_list_10 -> menu_list_superAdmin
-rw-r--r--   1 root     root         382 May 31 09:18 menu_list_5
-rw-r--r--   1 root     root         560 May 16 10:17 menu_list_admin
-rw-r--r--   1 root     root         560 May 31 09:17 menu_list_superAdmin
-rw-r--r--   1 root     root         382 May 14 16:10 menu_list_user
-rwxr-xr-x   1 root     root        1664 May 14 17:16 multi_choice
-rw-r--r--   1 confmgr  confmgr     2764 May 30 12:22 ports.db
-rw-r--r--   1 confmgr  confmgr   148565 May 30 17:11 zone_vm.log
</pre>
