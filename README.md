# devops-on-solaris
Creating a DevOps like on Solaris

This repository contains a copy of the Oracle Solaris Python DevOps Script as well as all related reqierd SMF and related startup scripts. compatible / tested with Oracle Solaris 11.3/11.4+

This document provides instructions on how to install and use the Solaris Python DevOps Script. the script helps automate Oracle Solaris Zone deployments as well as snap/cloning a ZFS associated file systems which then gets mounted in the zone by NFS, created on a ZFS Appliance. See the deployment notes for additional details.

<i>Script Options</i>.
<pre>
./clone_zfs.py -h
usage: clone_zfs.py [-h] -i  [-d | -r | -s]

Create VM(zone) with associated /apps1 clone.

optional arguments:
  -h, --help       show this help message and exit
  -i , --jiraid    associated Jira ID.
  -d, --delete     delete VM(zone) with associated snap.
  -r, --rotateImg  rotate VM(zone).
  -s, --imgStat    display VM(zone) IP / Port status.
</pre>

<h4>Versions</h4>

<b>Version 0.1</b>

Initial Release

<h3>Getting Started</h3>

<h4>Installation</h4>
<h4>Dependencies / Prerequisites</h4>
<b>The following Python libraries are required:</b>
<pre>
# Modules
import os ,sys, re
import time, datetime
import json
import logging
import argparse
import requests
requests.packages.urllib3.disable_warnings()

# Rad modules
#import rad.bindings.com.oracle.solaris.rad.zonesbridge as zbind
import rad.bindings.com.oracle.solaris.rad.zonemgr as zonemgr
import rad.bindings.com.oracle.solaris.rad.smf_1 as smf
import rad.client as radc
import rad.connect as radcon
import rad.auth as rada
</pre>
<i>Note: </i>You can install libraries by running <i>pip install [library] or (if available) by doing a pkg install [library] form the Oracle Solaris repository.</i>

<h4>Application Layout Details</h4>
The directory layout are explained below.
<ol>
<li><b>bin/clone_zfs.py: main script, to create/delete/stats clones</b></li>
<li><b>bin/fork_clones.py: stress test / fork script - run with with the argument [number simultaneous runs]</b></li>
<li><b>/opt/cloneFiles: directory contains smf related scripts - create on source zone to be cloned on evrey zone</b></li>
<li><b>/opt/cloneFiles/getIpPort.sh: script to populele the getIpPort SMF with IP Adress/Port information.</b></li>  
<li><b>/opt/cloneFiles/getIpPort.xml: smf to run the script to populele the getIpPort SMF with IP Adress/Port information.</b></li> 
<li><b>/opt/cloneFiles/mount_apps1.xml: smf to mount the ZFS cloned file system</b></li>
</ol>

For the full installation details you can follow this document <a href="docs/README.md">installation documentation</a>.
docs/index.html

<h4>Additional Detail</h4>
<p>Below is an exmaple workflow we are using.
<br><img src="images/devops_flow.png" alt="Solaris DevOps Workflow" align="middle" height="50%"></p>

<h4>Usage examples</h4>
To use the script, follow the steps below.
<pre>
./clone_zfs.py -h
usage: clone_zfs.py [-h] -i  [-d | -r | -s]

Create VM(zone) with associated /apps1 clone.

optional arguments:
  -h, --help       show this help message and exit
  -i , --jiraid    associated Jira ID.
  -d, --delete     delete VM(zone) with associated snap.
  -r, --rotateImg  rotate VM(zone).
  -s, --imgStat    display VM(zone) IP / Port status.
</pre>

To clone a zone just run something like the below.
<pre>
./clone_zfs.py -i jir10
Cloning VM/Zone z-1539798251-jir10 and associated file systems
Progress is being logged to zone_vm.log
--------------------------------
New VM/Zone z-1539798251-jir10 is available.
IP Address: 10.25.1.78
Port 32078
Installation of zone z-1539798251-jir10 successfully completed.
</pre>

And the log file will look something like the below.
<pre>
cat zone_vm.log
# Failed attempt.
2018-10-17 13:43:42,745:z-1539798222-jir10:INFO: Validating configuration request.
2018-10-17 13:43:43,048:z-1539798222-jir10:INFO: Snapshot snap_z-1539798222-jir10 is valid. continuing...
2018-10-17 13:43:43,385:z-1539798222-jir10:INFO: Clone apps1_z-1539798222-jir10 is valid. continuing...
2018-10-17 13:43:43,385:z-1539798222-jir10:INFO: Checking source zone availability...
2018-10-17 13:43:43,467:z-1539798222-jir10:ERROR: Source zone z-source, Stat: running, NOT available for cloning... exiting.

# Successful attempt.
2018-10-17 13:44:11,864:z-1539798251-jir10:INFO: Validating configuration request.
2018-10-17 13:44:12,172:z-1539798251-jir10:INFO: Snapshot snap_z-1539798251-jir10 is valid. continuing...
2018-10-17 13:44:12,582:z-1539798251-jir10:INFO: Clone apps1_z-1539798251-jir10 is valid. continuing...
2018-10-17 13:44:12,582:z-1539798251-jir10:INFO: Checking source zone availability...
2018-10-17 13:44:12,666:z-1539798251-jir10:INFO: Zone z-source is available(installed). continuing...
2018-10-17 13:44:12,666:z-1539798251-jir10:INFO: Configuring new zone: z-1539798251-jir10...
2018-10-17 13:44:13,295:z-1539798251-jir10:INFO: Configuring zone z-1539798251-jir10 successful.
2018-10-17 13:44:13,296:z-1539798251-jir10:INFO: All checks passed continuing.
2018-10-17 13:44:13,297:z-1539798251-jir10:INFO: Preparing zone z-1539798251-jir10. Setting zone properties...
2018-10-17 13:44:14,225:z-1539798251-jir10:INFO: Successfully set zone z-1539798251-jir10 properties.
2018-10-17 13:44:14,226:z-1539798251-jir10:INFO: Cerating snapshot: snap_z-1539798251-jir10
2018-10-17 13:44:14,939:z-1539798251-jir10:INFO: Snapshot created successfully.
2018-10-17 13:44:14,939:z-1539798251-jir10:INFO: Verifying snapshot availability.
2018-10-17 13:44:15,233:z-1539798251-jir10:INFO: Snapshot snap_z-1539798251-jir10 available. continuing...
2018-10-17 13:44:15,233:z-1539798251-jir10:INFO: CLONING file-systems
2018-10-17 13:44:15,233:z-1539798251-jir10:INFO: Source: /apps1
2018-10-17 13:44:15,234:z-1539798251-jir10:INFO: Destination: apps1_z-1539798251-jir10
2018-10-17 13:44:15,234:z-1539798251-jir10:INFO: Please wait...
2018-10-17 13:44:18,324:z-1539798251-jir10:INFO: Successfully created clone apps1_z-1539798251-jir10
2018-10-17 13:44:18,325:z-1539798251-jir10:INFO: CLONING VM/Zone
2018-10-17 13:44:18,327:z-1539798251-jir10:INFO: Source zone: z-source
2018-10-17 13:44:18,328:z-1539798251-jir10:INFO: Destination zone: z-1539798251-jir10
2018-10-17 13:44:18,329:z-1539798251-jir10:INFO: Please wait...
2018-10-17 13:44:59,777:z-1539798251-jir10:INFO: Successfully created zone z-1539798251-jir10
2018-10-17 13:44:59,779:z-1539798251-jir10:INFO: Booting VM/Zone z-1539798251-jir10 for the first time. Please wait...
2018-10-17 13:45:08,326:z-1539798251-jir10:INFO: Successfully booted VM/Zone z-1539798251-jir10.
2018-10-17 13:45:08,327:z-1539798251-jir10:INFO: Verifying VM/Zone z-1539798251-jir10 RAD connection availability.
2018-10-17 13:45:08,448:z-1539798251-jir10:INFO: RAD server is not accessible yet.
2018-10-17 13:45:09,513:z-1539798251-jir10:INFO: RAD server is not accessible yet.
2018-10-17 13:45:10,577:z-1539798251-jir10:INFO: RAD server is not accessible yet.
2018-10-17 13:45:11,637:z-1539798251-jir10:INFO: RAD server is not accessible yet.
2018-10-17 13:45:12,696:z-1539798251-jir10:INFO: RAD server is not accessible yet.
2018-10-17 13:45:13,848:z-1539798251-jir10:INFO: RAD server is accessible.
2018-10-17 13:45:13,909:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:15,923:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:18,236:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:20,343:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:29,002:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:31,017:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:33,031:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:35,113:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:37,146:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:39,162:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:41,178:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:43,194:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:45,208:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:47,223:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:49,238:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:51,255:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:53,270:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:55,284:z-1539798251-jir10:INFO: Waiting for network services to come ONLINE, curently OFFLINE.
2018-10-17 13:45:57,301:z-1539798251-jir10:INFO: Network services are now ONLINE. continuing.
2018-10-17 13:45:57,887:z-1539798251-jir10:INFO: Updating hostname to z-1539798251-jir10 successful.
2018-10-17 13:45:57,890:z-1539798251-jir10:INFO: Mounting apps1 in zone z-1539798251-jir10.
2018-10-17 13:45:57,918:z-1539798251-jir10:INFO: Mounting apps1 successful.
2018-10-17 13:45:57,920:z-1539798251-jir10:INFO: Getting z-1539798251-jir10 IP and Port information.
2018-10-17 13:45:57,953:z-1539798251-jir10:INFO: New VM/Zone is available with IP Address: 10.25.1.78 Port 32078
2018-10-17 13:45:57,956:z-1539798251-jir10:INFO: Installation of zone z-1539798251-jir10 successfully completed.
</pre>

To access the Zone/VM you just ssh to the global-zone port in this example 32078.
<pre>
ssh global-zone -p 32078
</pre>
Similar you can delete the zone by running the below.
<pre>
./clone_zfs.py -d -i jir10
Deleting VM/Zone z-1539798251-jir10 and associated snap_z-1539798251-jir10
Progress is being logged to zone_vm.log
--------------------------------
Uninstall/delete completed successfully.
</pre>

Log output
<pre>
2018-10-17 13:51:06,128:z-1539798251-jir10:INFO: Deleting VM/Zone z-1539798251-jir10.
2018-10-17 13:51:06,132:z-1539798251-jir10:INFO: Preparing removal of z-1539798251-jir10.
2018-10-17 13:51:06,134:z-1539798251-jir10:INFO: Halting z-1539798251-jir10 please wait...
2018-10-17 13:51:10,839:z-1539798251-jir10:INFO: Halting z-1539798251-jir10 completed successfully.
2018-10-17 13:51:10,839:z-1539798251-jir10:INFO: Uninstalling z-1539798251-jir10 please wait...
2018-10-17 13:51:18,020:z-1539798251-jir10:INFO: Uninstalling z-1539798251-jir10 completed successfully.
2018-10-17 13:51:18,023:z-1539798251-jir10:INFO: Deleteing z-1539798251-jir10 please wait...
2018-10-17 13:51:18,081:z-1539798251-jir10:INFO: Deleteing z-1539798251-jir10 completed successfully.
2018-10-17 13:51:18,081:z-1539798251-jir10:INFO: Uninstall/delete of VM/Zone z-1539798251-jir10 completed successfully.
2018-10-17 13:51:18,081:z-1539798251-jir10:INFO: Deleting clone/snapshot: apps1_z-1539798251-jir10
2018-10-17 13:51:21,669:z-1539798251-jir10:INFO: Clone/snapshot apps1_z-1539798251-jir10 and associated snap_z-1539798251-jir10 deleted successfully.
</pre>

zoneadm output on some cloned zones.
<pre>
zoneadm list -cv
  ID NAME             STATUS      PATH                         BRAND      IP    
   0 global           running     /                            solaris    shared
  99 z-1539623995-jir144 running     /zones/z-1539623995-jir144   solaris    excl  
 102 z-1539625421-jir145 running     /zones/z-1539625421-jir145   solaris    excl  
 105 z-1539625866-jir146 running     /zones/z-1539625866-jir146   solaris    excl  
 765 z-1539792929-jir100 running     /zones/z-1539792929-jir100   solaris    excl  
   - z-source         installed   /zones/z-source              solaris    excl  
</pr>

<p>Screen shout of the associated ZFS Appliance snap/clone(s).
<br><img src="images/zfssa-apps-snap.png" alt="ZFSSA snap/clones" align="middle" height="50%"></p>

<i>Note: </i>Additional details are avalble at <a href="http://www.devtech101.com/2018/10/18/creating-a-devops-like-environment-in-oracle-solaris-11-3-11-4-by-using-rad-and-rest-part-1/">Creating A DevOps Like Environment In Oracle Solaris 11.3/11.4 By Using RAD And REST</a>

<h4>License</h4>
This project is licensed under the MIT License - see the LICENSE file for details.
