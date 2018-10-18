#!/usr/bin/env python
#title           :clone_zfs.py
#description     :Creating a DevOps like on Solaris
#author          :Eli Kleinman
#date            :20181018
#version         :0.1
#usage           :python clone_zfs.py
#notes           :
#python_version  :2.7.14
#==============================================================================

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

# Argument Parser Options
parser = argparse.ArgumentParser(description='Create VM(zone) with associated /apps1 clone.')
parser.add_argument('-i', '--jiraid', metavar='', required=True, type=str, help='associated Jira ID.')

group = parser.add_mutually_exclusive_group(required=False)
group.add_argument('-d', '--delete', action='store_true', default=False, help='delete VM(zone) with associated snap.')
group.add_argument('-r', '--rotateImg', action='store_true', default=False, help='rotate VM(zone).')
group.add_argument('-s', '--imgStat', action='store_true', default=False, help='display VM(zone) IP / Port status.')
args = parser.parse_args()

# Set filesystem, zone-name
dt = datetime.datetime.now()
dst_zone = "z-"+ dt.strftime("%s") + "-" + args.jiraid

## Configure logging ##
log_dir = '/sc_profile_src/logs/'
logger = logging.getLogger(dst_zone)
logger.setLevel(logging.DEBUG)

# create a file handler
#log_output = log_dir + "zone_vm.log"
log_output = "zone_vm.log"
handler = logging.FileHandler(log_output)
handler.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s')
handler.setFormatter(formatter)

# add handler to logger
logger.addHandler(handler)

## End Configure logging ##

# ====================== ZFS related ======================

# Add proxy
#os.environ['http_proxy'] = "http://10.10.10.10:1234/"
#os.environ['https_proxy'] = "http://10.10.10.10:1234/"

# ZFSSA API URL
url = "https://10.250.109.110:215"

# ZFSSA API login 
zfsuser = ('admin')
zfspass = ('password')
zfsauth = (zfsuser,zfspass)

# ZFS pool
zfspool = "HP-pool1"

# ZFS project
zfsproject = "zfs-project"

# ZFS source filesystem
zfssrcfs = "apps1-fs1"

zfsdstsnap = 'snap_' + dst_zone
zfsdstclone = 'apps1_' + dst_zone

# Headers
jsonheader = {'Content-Type': 'application/json'}

# ====================== Global and Zone related =================

# Global zone
hostGz = 'solaris-global-name'

# Source zone
src_zone = "z-source"

# Zone template
sc_profile = 'sc_profile.xml'
sc_profile_dir = "/opt/" + sc_profile

# Dest zone
jiraid = args.jiraid

# ====================== End of settings ======================

# Create connection.
with radcon.connect_unix() as rc:
    rc=radcon.connect_ssh(hostGz)
    #rc=radcon.connect_tcp(hostGz, 12302)
    #print rc
#auth = rada.RadAuth(rc)
#auth.pam_login("root", 'password')

# ====================== Main call ===========================

def main():
    if args.delete:
        delete_vm()
        delete_filesystem()
    elif args.imgStat:
        displayImgStat(dst_zone)
    elif args.rotateImg:
        rotateImg(dst_zone)
    else:
        clone_filesystem()

# ====================== ZFSSA Reset Calls ===========================

def verif_snap(zfsdstsnap):
    r = requests.get("%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots/%s" % (url, zfspool, zfsproject, zfssrcfs, zfsdstsnap), auth=zfsauth, verify=False, headers=jsonheader)
    return r.status_code

def create_snap(zfsdstsnap):
    payload = { 'name': zfsdstsnap }
    r = requests.post("%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots" % (url, zfspool, zfsproject, zfssrcfs), auth=zfsauth, verify=False, headers=jsonheader, data=json.dumps(payload))
    return r.status_code

def verif_clone(zfsdstsnap, zfsdstclone):
    r = requests.get("%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s" % (url, zfspool, zfsproject, zfsdstclone), auth=zfsauth, verify=False, headers=jsonheader)
    return r.status_code

def create_clone(zfsdstsnap, zfsdstclone):
    payload = { 'share': zfsdstclone }
    r = requests.put("%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots/%s/clone" % (url, zfspool, zfsproject, zfssrcfs, zfsdstsnap), auth=zfsauth, verify=False, headers=jsonheader, data=json.dumps(payload))
    return r.status_code

def delete_snap(zfsdstsnap):
    r = requests.delete("%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots/%s" % (url, zfspool, zfsproject, zfssrcfs, zfsdstsnap), auth=zfsauth, verify=False, headers=jsonheader)
    return r.status_code

# ====================== End ZFSSA Reset calls =======================

def verify_zone_exist():

    zones = rc.list_objects(zonemgr.Zone())
    for i in range(0, len(zones)):
        zone = rc.get_object(zones[i])
        matchZone = re.search("-"+jiraid+"$", zone.name, flags=0)
        if matchZone is not None:
            return zone.name

def verify_src_zone(src_zone):
    z1_list = rc.list_objects(zonemgr.Zone(), 
                              radc.ADRGlobPattern({"name" : src_zone}))
    z1 = rc.get_object(z1_list[0])

    if z1.state == 'installed':
        logger.info("Zone %s is available(%s). continuing...", z1.name, z1.state)
        return z1
    else:
        closeCon()
        logger.error("Source zone %s, Stat: %s, NOT available for cloning... exiting.", z1.name, z1.state)
        sys.exit(1)

def verify_dst_zone():

    logger.info("Configuring new zone: %s...", dst_zone),
    matchZone = verify_zone_exist()
    if matchZone is not None:
        closeCon()
        logger.error("VM/Zone for %s exists with zone name %s.", jiraid, dst_zone)
        print "\nERROR: VM/Zone for %s exists with the zone name %s." % (jiraid, dst_zone)
        sys.exit(1)

    zonemanager = rc.get_object(zonemgr.ZoneManager())
    zonemanager.create(dst_zone, None, "SYSsolaris")

    z2_list = rc.list_objects(zonemgr.Zone(),
                              radc.ADRGlobPattern({"name" : dst_zone}))
    z2 = rc.get_object(z2_list[0])

    if z2.state == 'configured':
        logger.info("Configuring zone %s successful.", dst_zone)
        return z2
    else:
        closeCon()
        logger.error("Destination zone %s is NOT available for cloning. zone stat is in %s... exiting.", z2.name, z2.stat)
        sys.exit(1)

def prep_zone(z2):
        logger.info("Preparing zone %s. Setting zone properties...", z2.name),
        z2.editConfig()
        resource = zonemgr.Resource('global')
        prop1 = zonemgr.Property('autoboot','true')
        prop2 = zonemgr.Property('zonepath','/zones/%{zonename}')
        z2.setResourceProperties(resource,[prop1])
        z2.setResourceProperties(resource,[prop2])
        z2.commitConfig()
        z2.editConfig()
        z2.setResourceProperties(
            zonemgr.Resource('anet', [zonemgr.Property('linkname', 'net0')]),
                                     [ zonemgr.Property('lower-link', 'etherstub0')])
        z2.commitConfig()
        logger.info("Successfully set zone %s properties.", z2.name)

def clone_zone(z1, z2):

    options = ['-c', sc_profile_dir]
    options.extend([z1.name])

    z2.clone(options=options)

def boot_zone(z2):

    if z2.state == 'installed':
        # Boot VM/Zone.
        logger.info("Booting VM/Zone %s for the first time. Please wait...", z2.name)
        z2_pat = radc.ADRGlobPattern({"name" : z2.name})
        z2_boot = rc.get_object(zonemgr.Zone(), z2_pat)
        z2_boot.boot(None)
        logger.info("Successfully booted VM/Zone %s.", z2.name)
    else:
        logger.error("%s Faild to boot.", z2.name)

def connectToZone(z2):
    logger.info("Verifying VM/Zone %s RAD connection availability.", z2.name)
    while z2.state != "running":
        logger.info("VM/Zone is state: %s", z2.state)
        time.sleep(1)

    while True:
        try:
            global zcon
            zcon = radcon.connect_zone(rc, z2.name, "root")
            logger.info("RAD server is accessible.")
            break
        except:
            logger.info("RAD server is not accessible yet.")
            time.sleep(1)
            pass

    network_instance = zcon.get_object(smf.Instance(),
                              radc.ADRGlobPattern({"service" : "milestone/network",
                                                        "instance" : "default"}))

    while str(network_instance.state) != "ONLINE":
        logger.info("Waiting for network services to come ONLINE, curently %s.", network_instance.state)
        time.sleep(2)


def setHostname(z2):

    #services = zcon.list_objects(smf.Service())
    node_instance = zcon.get_object(smf.Instance(),
                              radc.ADRGlobPattern({"service" : "system/identity",
                                                        "instance" : "node"}))
    logger.info("Network services are now ONLINE. continuing.")
    orig_type = node_instance.readProperty("config/nodename").type
    node_instance.writeProperty("config/nodename", orig_type, [z2.name])
    node_instance.writeProperty("config/loopback", orig_type, [z2.name])
    logger.info("Updating hostname to %s successful.", z2.name)

def mountApps1(z2):
    logger.info("Mounting apps1 in zone %s.", z2.name)
    apps1_instance = zcon.get_object(smf.Instance(),
                              radc.ADRGlobPattern({"service" : "application/apps1_mount",
                                                        "instance" : "default"}))
    apps1_instance.enable ("")
    logger.info("Mounting apps1 successful.")


def getIpPort(z2):

    logger.info("Getting %s IP and Port information.", z2.name)
    getIp_instance = zcon.get_object(smf.Instance(),
                              radc.ADRGlobPattern({"service" : "network/getIpPort",
                                                        "instance" : "ip"}))
    getIp_instance.refresh()
    ipAddr = getIp_instance.readProperty("config/ip_addr").values[0]
    ipPort = getIp_instance.readProperty("config/ip_port").values[0]
    logger.info("New VM/Zone is available with IP Address: %s Port %s", ipAddr, ipPort)
    print "New VM/Zone %s is available. \nIP Address: %s \nPort %s" % (z2.name, ipAddr, ipPort)

def displayImgStat(dst_zone):
    
    logger.info("Pulling status...")
    print "Pulling status...\n------------------------------"
    matchZone = verify_zone_exist()
    snap = verif_snap(zfsdstsnap)

    if (matchZone is None and snap != 200):
       closeCon()
       print "ERROR: No VM/Zone %s or associated clone %s found." % (dst_zone, zfsdstsnap)
       sys.exit(1)
    else:

       z2_list = rc.list_objects(zonemgr.Zone(),
                              radc.ADRGlobPattern({"name" : matchZone}))
       z2 = rc.get_object(z2_list[0])

       if z2.state != 'running':
           closeCon()
           logger.error("VM/Zone %s is not available, curent zone stat is %s.", matchZone, z2.state)
           print "VM/Zone %s is not available, curent zone stat is %s." % (matchZone, z2.state)
           sys.exit(0)
       else:
           connectToZone(z2)
           getIpPort(z2)
           closeCon()
           print "Mount src: apps1_%s" % (matchZone)
           print "Mount dst: /apps1"

def rotateImg(ds):
    print "Not implemented yet."

def closeCon():
    try: rc.close()
    except NameError: rc = None
    try: zcon.close()
    except NameError: zcon = None

# ********************** Main calls ********************** #

def clone_filesystem():

    print "Cloning VM/Zone %s and associated file systems\nProgress is being logged to %s\n--------------------------------" % (dst_zone, log_output)
    logger.info('Validating configuration request.')
    snap = verif_snap(zfsdstsnap)
    if snap == 200:
        closeCon()
        print "Snapshot %s exists. Error code: %s  \nExiting." % (zfsdstsnap, snap)
        logger.error("Snapshot %s exists. Error code: %s  exiting.", zfsdstsnap, snap)
        sys.exit(snap)
    else:
        logger.info("Snapshot %s is valid. continuing...", zfsdstsnap)

    clone = verif_clone(zfsdstsnap, zfsdstclone)
    if clone == 200:
        closeCon()
        print "Clone %s exists. Error code: %s \nExiting." % (zfsdstclone)
        logger.error("Clone %s exists. Error code: %s exiting.", zfsdstclone, clone)
        sys.exit(snap)
    else:
        logger.info("Clone %s is valid. continuing...", zfsdstclone)

    # Checking source zone availability.
    logger.info("Checking source zone availability...")
    src_z = verify_src_zone(src_zone)

    # Configuring destination zone.
    dst_z = verify_dst_zone()
    logger.info("All checks passed continuing.")
    prep_zone(dst_z)

    # Create ZFS snap.
    logger.info("Cerating snapshot: %s", zfsdstsnap)
    snap = create_snap(zfsdstsnap)
    if snap == 201:
        logger.info("Snapshot created successfully.")
    else:
        closeCon()
        logger.error("Snapshot %s creation failed, with error code: %s. exiting.", zfsdstsnap, snap)
        print("Snapshot %s creation failed, with error code: %s \nExiting.") % (zfsdstsnap, snap)
        sys.exit(snap)

    # Verifying ZFS snap availability.
    logger.info("Verifying snapshot availability.")
    snap = verif_snap(zfsdstsnap)
    if snap == 200:
        logger.info("Snapshot %s available. continuing...", zfsdstsnap)
    else:
        closeCon()
        logger.error("Error: Snapshot %s is not available. Return error code is: %s. exiting.", zfsdstsnap, snap)
        print("Error: Snapshot %s is not available. Return error code is: %s \nExiting.") % (zfsdstsnap, snap)
        sys.exit(snap)

    # Cloning /apps1 file-systems.
    logger.info("CLONING file-systems")
    logger.info("Source: /apps1")
    logger.info("Destination: %s",  zfsdstclone)
    logger.info("Please wait...")
    clone = create_clone(zfsdstsnap, zfsdstclone)
    if clone == 201:
        logger.info("Successfully created clone %s",  zfsdstclone)
    else:
        logger.error("Clone %s creation failed. Return error code is: %s. exiting.",  zfsdstclone, clone)
        closeCon()
        print("Clone %s creation failed. Return error code is: %s \nExiting.") % (zfsdstclone, clone)
        sys.exit(1)

    # Clone source to destination zone.
    logger.info("CLONING VM/Zone")
    logger.info("Source zone: %s", src_z.name)
    logger.info("Destination zone: %s", dst_z.name)
    logger.info("Please wait...")
    clone_zone(src_z, dst_z)
    logger.info("Successfully created zone %s", dst_z.name)

    # Boot zone.
    boot_zone(dst_z)

    ## Prep zone ##
    #
    # Check for zone availability.
    connectToZone(dst_z)
    # Set zone hostname.
    setHostname(dst_z)
    # Set zone hostname.
    mountApps1(dst_z)
    # Get zone IP adn Port.
    getIpPort(dst_z)
    # Close connection.
    closeCon()

    logger.info("Installation of zone %s successfully completed.", dst_z.name)
    print "Installation of zone %s successfully completed." % (dst_z.name)

def delete_filesystem():

    logger.info("Deleting clone/snapshot: apps1_%s", matchZone)
    delete_clone =  delete_snap('snap_' + matchZone)
    if delete_clone == 204:
        logger.info("Clone/snapshot apps1_%s and associated snap_%s deleted successfully.", matchZone, matchZone)
    else:
        closeCon()
        print("ERROR: Clone snap_%s deletion failed. Return error code is: %s \nExiting.") % (matchZone, delete_clone)
        sys.exit(1)

def delete_vm():

    global matchZone
    matchZone = verify_zone_exist()
    if matchZone is None:
        closeCon()
        print "ERROR: Cannot find VM/Zone for %s." % (jiraid)
        sys.exit(1)
    logging.addLevelName(logging.DEBUG, matchZone)

    print "Deleting VM/Zone %s and associated snap_%s\nProgress is being logged to %s\n--------------------------------" % (matchZone, matchZone, log_output)
    logger.info("Deleting VM/Zone %s.", matchZone)

    z2_list = rc.list_objects(zonemgr.Zone(),
                              radc.ADRGlobPattern({"name" : matchZone}))
    if not z2_list:
       closeCon()
       print "ERROR: VM/Zone does not exist, please verify the spelling is correct."
       sys.exit(1)

    z2 = rc.get_object(z2_list[0])

    logger.info("Preparing removal of %s.", matchZone)
    if z2.state == "running":
        logger.info("Halting %s please wait...", matchZone)
        z2.halt(None)
        logger.info("Halting %s completed successfully.", matchZone)
        logger.info("Uninstalling %s please wait...", matchZone)
        z2.uninstall(['-F'])
        logger.info("Uninstalling %s completed successfully.", matchZone)
    elif z2.state == "incomplete":
        logger.info("Uninstalling %s please wait...", matchZone)
        z2.uninstall(['-F'])
        logger.info("Uninstalling %s completed successfully.", matchZone)
    else:
        logger.info("Uninstall not required for zone %s in state %s.", z2.name, z2.state)
    logger.info("Deleteing %s please wait...", z2.name)
    delete_zone = rc.get_object(zonemgr.ZoneManager())
    delete_zone.delete(z2.name)
    closeCon()
    logger.info("Deleteing %s completed successfully.", matchZone)
    logger.info("Uninstall/delete of VM/Zone %s completed successfully.", matchZone)
    print "Uninstall/delete completed successfully."

if __name__ == "__main__":
    main()
