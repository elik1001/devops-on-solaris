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


<b>Version 0.5</b>

<b>Added: </b>This version adds the VM/Zone image rotate i.e. <b>-r (--rotateImg)</b> option.
<br>With this version you can now update/rollback an image using the newest ZFS copy.

<i>For example:</i>
<br>z-12345-jir1 was created on 10/1
<br>Then
<br>z-12345-jir2 was created on 10/2
<br>then
<br>z-12345-jir3 was created on 10/3
<br>If you <i>remove z-12345-jir2</i> all changes/updates consume disk space eve it was deleted, it will only be freed if <i>z-12345-jir1</i> will be removed which is still in use.

To get around this issue.

You can use the option <b>-r</b> which will clone/create a new zfs file system in  <i>z-12345-jir1</i> with the prefix of <i>_clone</i>.

Next, it will copy by using <i>rsync --delete</i> to back-date the clone with the original content.

Finlay, it will switch / rename mount points and snaps.
<br><i>Note: </i>Currently the original image / snap will only be renamed with a time stamp and original name,
if all checks out to be good you manually deleted the image, once this functionally is fully tested I will add to auto delete the old original image/snap.

<b>Updated: </b>With this updated the VM/Zone deleted option was also updated.
<br>Since you can now have multiple snaps/clones for the same VM/zone.
<br>If you use the <b>-d</b> option the system will remove the VM/zone as well as all associated snaps/clones.

<b>Updated: </b>Created new directory <i>cloneFiles/conf</i> and <i>cloneFiles/bin</i>, all executable files ware moved to bin and all xml ware moved to conf, the xml files ware updated with the new file path.

<b>Updated: </b>Added a service for rsync <i>application/apps1_mount:apps1sync</i>, it will look like the below.
<pre>
disabled       11:40:15 svc:/application/apps1_mount:apps1sync
disabled       11:40:15 svc:/application/apps1_mount:apps1dst
disabled       11:40:15 svc:/application/apps1_mount:apps1src
</pre>

<b>Version 0.3</b>

Added Network digram

<b>Version 0.2</b>

Added sc_profile.xml example

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
<li><b>bin/clone_zfs.py:</b> main script, to create/delete/stats clones</li>
<li><b>bin/fork_clones.py:</b> stress test / fork script - run with with the argument [number simultaneous runs]</li>
<li><b>/opt/cloneFiles:</b> directory contains smf related scripts - create on source zone to be cloned on evrey zone</li>
<li><b>/opt/cloneFiles/getIpPort.sh:</b> script to populele the getIpPort SMF with IP Adress/Port information.</li>  
<li><b>/opt/cloneFiles/getIpPort.xml:</b> smf to run the script to populele the getIpPort SMF with IP Adress/Port information.</li> 
<li><b>/opt/cloneFiles/mount_apps1.xml:</b> smf to mount the ZFS cloned file system</li>
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
Similar you can delete the zone by running the below (it will delete all associated snaps/clones).
<pre>
./clone_zfs.py -d -i jir10
Deleting VM/Zone z-1539798251-jir10 and associated snap_z-1539798251-jir10
Progress is being logged to zone_vm.log
--------------------------------
Uninstall/delete completed successfully.
</pre>

Log output - with associated snaps/clones.
<pre>
2018-10-26 11:36:46,920:z-1540563221-jir112:INFO: Deleting VM/Zone z-1540563221-jir112.
2018-10-26 11:36:46,923:z-1540563221-jir112:INFO: Preparing removal of z-1540563221-jir112.
2018-10-26 11:36:46,924:z-1540563221-jir112:INFO: Halting z-1540563221-jir112 please wait...
2018-10-26 11:36:51,904:z-1540563221-jir112:INFO: Halting z-1540563221-jir112 completed successfully.
2018-10-26 11:36:51,904:z-1540563221-jir112:INFO: Uninstalling z-1540563221-jir112 please wait...
2018-10-26 11:36:59,186:z-1540563221-jir112:INFO: Uninstalling z-1540563221-jir112 completed successfully.
2018-10-26 11:36:59,188:z-1540563221-jir112:INFO: Deleteing z-1540563221-jir112 please wait...
2018-10-26 11:36:59,238:z-1540563221-jir112:INFO: Deleteing configuration of z-1540563221-jir112 completed successfully.
2018-10-26 11:36:59,238:z-1540563221-jir112:INFO: Deleting clone/snapshots related to zone: z-1540563221-jir112
2018-10-26 11:36:59,238:z-1540563221-jir112:INFO: Vaildating snaps related to zone snap_z-1540563221-jir112
2018-10-26 11:36:59,525:z-1540563221-jir112:INFO: Snap snap_z-1540563221-jir112 related to zone snap_z-1540563221-jir112, will be deleted.
2018-10-26 11:36:59,525:z-1540563221-jir112:INFO: Snap snap_z-1540563221-jir112-1540563444 related to zone snap_z-1540563221-jir112, will be deleted.
2018-10-26 11:36:59,525:z-1540563221-jir112:INFO: Snap snap_z-1540563221-jir112-1540563473 related to zone snap_z-1540563221-jir112, will be deleted.
2018-10-26 11:36:59,525:z-1540563221-jir112:INFO: Deleting clone/snapshot snap_z-1540563221-jir112
2018-10-26 11:37:02,883:z-1540563221-jir112:INFO: Clone/snapshot apps1_snap_z-1540563221-jir112 and associated snap_snap_z-1540563221-jir112 deleted successfully.
2018-10-26 11:37:02,884:z-1540563221-jir112:INFO: Deleting clone/snapshot snap_z-1540563221-jir112-1540563444
2018-10-26 11:37:06,343:z-1540563221-jir112:INFO: Clone/snapshot apps1_snap_z-1540563221-jir112-1540563444 and associated snap_snap_z-1540563221-jir112-1540563444 deleted successfully.
2018-10-26 11:37:06,343:z-1540563221-jir112:INFO: Deleting clone/snapshot snap_z-1540563221-jir112-1540563473
2018-10-26 11:37:09,598:z-1540563221-jir112:INFO: Clone/snapshot apps1_snap_z-1540563221-jir112-1540563473 and associated snap_snap_z-1540563221-jir112-1540563473 deleted successfully.
2018-10-26 11:37:09,599:z-1540563221-jir112:INFO: Uninstall/delete of VM/Zone z-1540563221-jir112 completed successfully.
</pre>

Rotaing a zone.
<pre>
./clone_zfs.py -r -i jir111
Rotating /apps1(apps1_z-1540500938-jir111) in zone z-1540500938-jir111.. please wait...
Rotation of /apps1(apps1_z-1540500938-jir111) in zone z-1540500938-jir111 completed successfully.
</pre>

Log output - rotaing a zone.
<pre>
2018-10-26 10:18:45,588:z-1540563400-jir11:INFO: Validating VM/Zone status.. please wait...
2018-10-26 10:18:46,054:z-1540563400-jir11:INFO: Rotating /apps1(apps1_z-1540563400-jir11) in zone z-1540563400-jir11...
2018-10-26 10:18:46,058:z-1540563400-jir11:INFO: Verifying VM/Zone z-1540563400-jir11 RAD connection availability.
2018-10-26 10:18:46,237:z-1540563400-jir11:INFO: RAD server is accessible.
2018-10-26 10:18:46,277:z-1540563400-jir11:INFO: Cerating snapshot: snap_z-1540563525-jir11
2018-10-26 10:18:46,876:z-1540563400-jir11:INFO: Snapshot created successfully.
2018-10-26 10:18:46,877:z-1540563400-jir11:INFO: CLONING file-systems
2018-10-26 10:18:46,877:z-1540563400-jir11:INFO: Source: /apps1
2018-10-26 10:18:46,877:z-1540563400-jir11:INFO: Destination: apps1_z-1540563525-jir11
2018-10-26 10:18:46,877:z-1540563400-jir11:INFO: Please wait...
2018-10-26 10:18:49,593:z-1540563400-jir11:INFO: Successfully created clone apps1_z-1540563525-jir11
2018-10-26 10:18:49,593:z-1540563400-jir11:INFO: Setting apps1_z-1540563525-jir11 as /apps1_clone.
2018-10-26 10:18:49,621:z-1540563400-jir11:INFO: Successfully set apps1_z-1540563525-jir11 as /apps1_clone mount.
2018-10-26 10:18:49,623:z-1540563400-jir11:INFO: Enabling service related to mount apps1_z-1540563525-jir11, in zone z-1540563400-jir11.
2018-10-26 10:18:49,644:z-1540563400-jir11:INFO: Service enabled for apps1_z-1540563525-jir11 mount. successful.
2018-10-26 10:18:49,646:z-1540563400-jir11:INFO: Enabling service related to mount rsync, in zone z-1540563400-jir11.
2018-10-26 10:18:49,667:z-1540563400-jir11:INFO: Service enabled for rsync mount. successful.
2018-10-26 10:18:50,685:z-1540563400-jir11:INFO: Disableing service related to mount NA in zone z-1540563400-jir11.
2018-10-26 10:18:50,705:z-1540563400-jir11:INFO: Service enabled for NA mount successful.
2018-10-26 10:18:50,706:z-1540563400-jir11:INFO: Sync to /apps1_clone(apps1_z-1540563525-jir11) completed sucssfuly.
2018-10-26 10:18:50,708:z-1540563400-jir11:INFO: Disableing service related to mount rsync in zone z-1540563400-jir11.
2018-10-26 10:18:50,720:z-1540563400-jir11:INFO: Service enabled for rsync mount successful.
2018-10-26 10:18:50,721:z-1540563400-jir11:INFO: Disableing service related to mount apps1_z-1540563525-jir11 in zone z-1540563400-jir11.
2018-10-26 10:18:50,737:z-1540563400-jir11:INFO: Service enabled for apps1_z-1540563525-jir11 mount successful.
2018-10-26 10:18:50,738:z-1540563400-jir11:INFO: Disableing service related to mount apps1_z-1540563400-jir11 in zone z-1540563400-jir11.
2018-10-26 10:18:50,757:z-1540563400-jir11:INFO: Service enabled for apps1_z-1540563400-jir11 mount successful.
2018-10-26 10:18:50,757:z-1540563400-jir11:INFO: Renaming snap: from snap_z-1540563400-jir11 to snap_z-1540563400-jir11.
2018-10-26 10:18:51,504:z-1540563400-jir11:INFO: Renaming clone: from apps1_z-1540563400-jir11 to apps1_z-1540563400-jir11.
2018-10-26 10:18:53,847:z-1540563400-jir11:INFO: Renaming snap: from snap_z-1540563525-jir11 to snap_z-1540563525-jir11.
2018-10-26 10:18:54,515:z-1540563400-jir11:INFO: Renaming clone: from apps1_z-1540563525-jir11 to apps1_z-1540563525-jir11.
2018-10-26 10:18:57,042:z-1540563400-jir11:INFO: Enabling service related to mount apps1_z-1540563400-jir11, in zone z-1540563400-jir11.
2018-10-26 10:18:57,058:z-1540563400-jir11:INFO: Service enabled for apps1_z-1540563400-jir11 mount. successful.
2018-10-26 10:18:57,058:z-1540563400-jir11:INFO: Rotation of /apps1(apps1_z-1540563400-jir11) in zone z-1540563400-jir11 completed successfully.
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
</pre>

<p>Screen shout of the associated ZFS Appliance snap/clone(s).
<br><img src="images/zfssa-apps-snap.png" alt="ZFSSA snap/clones" align="middle" height="50%"></p>

<i>Note: </i>Additional details are avalble at <a href="http://www.devtech101.com/2018/10/18/creating-a-devops-like-environment-in-oracle-solaris-11-3-11-4-by-using-rad-and-rest-part-1/">Creating A DevOps Like Environment In Oracle Solaris 11.3/11.4 By Using RAD And REST</a>

<h4>License</h4>
This project is licensed under the MIT License - see the LICENSE file for details.
