#!/usr/bin/env python
#title           :clone_zfs.py
#description     :Creating a DevOps like on Solaris
#author          :Eli Kleinman
#release date    :20181018
#update date     :20181121
#version         :0.6
#usage           :python clone_zfs.py
#notes           :
#python_version  :2.7.14
#==============================================================================

# RAD modules
import rad.bindings.com.oracle.solaris.rad.zonemgr as zonemgr
import rad.bindings.com.oracle.solaris.rad.smf_1 as smf
import rad.bindings.com.oracle.solaris.rad.kstat_1 as kbind
import rad.client as radc
import rad.connect as radcon
import rad.auth as rada
# import rad.bindings.com.oracle.solaris.rad.zonesbridge as zbind

# General modules
import os
import re
import sys
import time
import datetime
import json
import logging
import argparse
import pickledb
from subprocess import PIPE, Popen
from multiprocessing import Process
import requests
requests.packages.urllib3.disable_warnings()

# Argument Parser Options
parser = argparse.ArgumentParser(
    description='Create VM(zone) with associated /apps1 clone'
    )
parser.add_argument('-e', '--env', nargs='?', default='dev', type=str,
                    choices=['test', 'dev', 'stage'],
                    help='select environment dev, test, stage(default is dev)')
group1 = parser.add_mutually_exclusive_group()
group1.add_argument('-s', '--imgStat', action='store_true', default=False,
                    help='display VM(zone) IP / Port status')
group1.add_argument('-d', '--delete', action='store_true', default=False,
                    help='delete VM(zone) with associated snap')
group1.add_argument('-r', '--rotateImg', action='store_true', default=False,
                    help='rotate VM(zone).')

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-i', '--jiraid', metavar='', required=False, type=str,
                   help='associated Jira ID')
group.add_argument('-l', '--listZones', nargs='?', const="listZones",
                   default=None, required=False, type=str,
                   help='List all Active Zone resources')
args = parser.parse_args()

# Get date and time
dt = datetime.datetime.now()

if args.listZones is not None:
    if args.delete or args.imgStat or args.rotateImg:
        d = {'app_name': sys.argv[0]}
        print """usage: {app_name} [-h] [-l [LISTZONES]] [-e [ENV]] -i
                           [-d | -r | -s]
{app_name}: error: argument -i/--jiraid is required""".format(**d)
        sys.exit(0)
    else:
        # Set filesystem, zone-name
        dst_zone = "z-" + dt.strftime("%s") + "-" + "status"
        pass
else:
    # Set filesystem, zone-name
    dst_zone = "z-" + dt.strftime("%s") + "-" + args.jiraid

# Set working environment(defaults to dev).
work_env = args.env


def set_logging(logName):
    """Configure  / set all logging related settings"""
    global logger, handler, formatter, log_output
    log_dir = '/sc_profile_src/logs/'
    logger = logging.getLogger(logName)
    logger.setLevel(logging.DEBUG)

    # create a file handler
    log_output = "zone_vm.log"
    handler = logging.FileHandler(log_output)
    handler.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s:%(name)s:%(levelname)s: %(message)s'
        )
    handler.setFormatter(formatter)

    # add handler to logger
    logger.addHandler(handler)


# ====================== ZFS related ======================

# Add proxy
# os.environ['http_proxy'] = "http://10.10.10.10:1234/"
# os.environ['https_proxy'] = "http://10.10.10.10:1234/"

# ZFSSA API URL
url = "https://10.250.109.110:215"


# ZFSSA API login
zfsuser = ('admin')
zfspass = ('password')
zfsauth = (zfsuser, zfspass)

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

# Global zone - will the one with the lowest CPU load.
# Define dr state, can be ha, dr or both.
dclist = ['ha', 'dr']
drstat = "both"

# Define a list of Global Zone set of HA and DR.
hostdclist = [
    {'id': 1, 'ha': 'dc1-host1-gz', 'dr': 'dc2-host1-gz'},
    {'id': 2, 'ha': 'dc1-host2-gz', 'dr': 'dc2-host2-gz'},
    {'id': 3, 'ha': 'dc1-host3-gz', 'dr': 'dc2-host3-gz'},
    {'id': 4, 'ha': 'dc1-host4-gz', 'dr': 'dc2-host4-gz'},
    ]

# Min Load and Memory required for Global Zones
loadvalue = 30
minmem = 20000

# Lowest / first port used for connections - firewall mapping
low_port = 31011

# Source zone
src_zone = "z-source"

# Dest (Jira) zone name
jiraid = args.jiraid

# ====================== End of settings ======================

# ====================== Main call ===========================


def main(dc, host):
    """Main calling program selector.
    the selected program will spawn in parallel two 
    executions(HA and DR), one execution per data center.
    """
    if args.delete:
        p = Process(target=delete_vm, args=(dc, host,))
        p.start()
    elif args.imgStat:
        p = Process(target=display_img_stat, args=(dc, host, dst_zone,))
        p.start()
    elif args.rotateImg:
        rotate_img(dc, host, dst_zone)
    elif args.listZones is not None:
        perf = get_system_resources(dc, host)
        print "-----------========= " + dc.upper() + " ==========----------"
        print json.dumps(perf, indent=4, sort_keys=True)
    else:
        p = Process(target=clone_vm_fs, args=(dc, host,))
        p.start()

# ====================== ZFSSA Reset Calls ===========================


def verif_snap(zfsdstsnap):
    """Verify the ZFS snapshot name already exists.
    accepts: a zfs snapshot name.
    returns: the ZFS return status code.
    """
    r = requests.get(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots/%s"
        % (url, zfspool, zfsproject, zfssrcfs, zfsdstsnap),
        auth=zfsauth, verify=False, headers=jsonheader,
        )
    return r.status_code


def create_snap(zfsdstsnap):
    """Create a ZFS snapshot.
    accepts: a zfs snapshot name.
    returns: the ZFS return status code.
    """
    payload = {'name': zfsdstsnap}
    r = requests.post(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots"
        % (url, zfspool, zfsproject, zfssrcfs), auth=zfsauth, verify=False,
        headers=jsonheader, data=json.dumps(payload),
        )
    return r.status_code


def rename_snap(zfssrcsnap, zfsdstsnap):
    """Renames a ZFS snapshot.
    accepts: the source and destination zfs snapshot name.
    returns: the ZFS return status code.
    """
    logger.info("Renaming snap: from %s to %s.", zfssrcsnap, zfsdstsnap)
    payload = {'name': zfsdstsnap}
    r = requests.put(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots/%s"
        % (url, zfspool, zfsproject, zfssrcfs, zfssrcsnap),
        auth=zfsauth, verify=False, headers=jsonheader,
        data=json.dumps(payload),
        )
    return r.status_code


def create_clone(zfsdstsnap, zfsdstclone):
    """Creates a ZFS clone based on an exsistng snapshot.
    accepts: the exsistng ZFS snapshot name, new ZFS clone name.
    returns: the ZFS return status code.
    """
    payload = {'share': zfsdstclone}
    r = requests.put(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots/%s/clone"
        % (url, zfspool, zfsproject, zfssrcfs, zfsdstsnap),
        auth=zfsauth, verify=False, headers=jsonheader, data=json.dumps(payload),
        )
    return r.status_code


def verif_clone(zfsdstsnap, zfsdstclone):
    """Verify a ZFS clone exsist.
    accepts: the exsistng ZFS snapshot and clone name.
    returns: the ZFS return status code.
    """
    r = requests.get(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s"
        % (url, zfspool, zfsproject, zfsdstclone),
        auth=zfsauth, verify=False, headers=jsonheader,
        )
    return r.status_code


def rename_clone(zfssrcclone, zfsdstclone):
    """Rename a ZFS clone.
    accepts: the exsistng ZFS clone name, and new ZFS clone name.
    returns: the ZFS return status code.
    """
    logger.info("Renaming clone: from %s to %s.", zfssrcclone, zfsdstclone)
    payload = {'name': zfsdstclone}
    r = requests.put(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s"
        % (url, zfspool, zfsproject, zfssrcclone),
        auth=zfsauth, verify=False, headers=jsonheader,
        data=json.dumps(payload),
        )
    return r.status_code


def get_snap_list(zone):
    """Gather list of ZFS clone/snapshots related to a Zone.
    accepts: the exsistng Zone name.
    returns: list of ZFS clone/snapshots.
    """
    logger.info("Searching for snaps related to zone %s", zone)
    r = requests.get(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots"
        % (url, zfspool, zfsproject, zfssrcfs),
        auth=zfsauth, verify=False, headers=jsonheader,
        )
    data = r.json()
    snaps = data['snapshots']
    snaplist = []
    for snap in snaps:
        if re.search(zone, snap['name']):
            snaplist.append(snap['name'])
    logger.info("Found %s snap/clones related to zone %s.", len(snaplist), zone)
    return snaplist


def delete_snap(zfsdstsnap):
    """Delete a ZFS clone/snapshots.
    accepts: the exsistng snapshots.
    returns: the ZFS return status code.
    """
    r = requests.delete(
        "%s/api/storage/v1/pools/%s/projects/%s/filesystems/%s/snapshots/%s"
        % (url, zfspool, zfsproject, zfssrcfs, zfsdstsnap),
        auth=zfsauth, verify=False, headers=jsonheader,
        )
    return r.status_code

# ====================== End ZFSSA Reset calls =======================


def close_con():
    """Close  Global and Non-Global zone connections"""
    try:
        rc.close()
    except NameError:
        rc = None
    try:
        zcon.close()
    except NameError:
        zcon = None

# ====================== Global Zone Connection ======================


def dc_host_list(hostdclist, dc):
    """Split the two data center server list.
    accepts: host dictionary, data center list.
    returns: single data center server dictionary.
    """
    host_grp = []
    for i in hostdclist:
        d = {'id': i['id'], dc: i[dc]}
        host_grp.append(d)
    return host_grp


def host_connect(host):
    """Open / create server RAD connection. """
    global rc
    with radcon.connect_unix() as rc:
        rc = radcon.connect_ssh(host)
    # auth = rada.RadAuth(rc)
    # auth.pam_login("root", 'password')


def get_zone_count():
    """Get active / running non-global Zone count.
    returns: active / running Zone count.
    """
    zones = rc.list_objects(zonemgr.Zone())
    z_run = []
    for z in zones:
        z_list = rc.list_objects(
                     zonemgr.Zone(), radc.ADRGlobPattern({"name": z.name})
                     )
        zl = rc.get_object(z_list[0])
        if zl.state == "running":
            z_run.append(zl)
    return len(z_run)


def get_system_load(className, moduleName, instNum, propName):
    """Retrieve a particular kstat.
    accepts: class Name, module Name, instance Number, property Name.
    returns: kstat load or available value.
    """
    pat = radc.ADRGlobPattern(
              {"class": className,
               "module": moduleName,
               "instance": instNum,
               "name": propName}
          )
    kstat = rc.get_object(kbind.Kstat(), pat)

    # Do something with the kstat data.
    data = kstat.fresh_snapshot().data
    assert data.discriminant == kbind.Kstype.NAMED
    for named in data.NAMED:
        if (
               named.name == "avenrun_15min" or named.name == "freemem" or
               named.name == "slab_size"
           ):
            return (getattr(named.value, str(named.value.discriminant)))


def verify_zone_exist():
    """Verifies / checks if a zone name exist.
    returns: the zone name.
    """
    zones = rc.list_objects(zonemgr.Zone())
    for i in range(0, len(zones)):
        zone = rc.get_object(zones[i])
        if re.search("-"+jiraid+"$", zone.name):
            return zone.name


def get_system_resources(dc, host_grp):
    """Checks each Gloab Zone system resources.
    accepts: data center, host dictionary list.
    returns: dictionary with each Global Zone resource performance.
    """
    if args.listZones is not None:
        set_logging(dst_zone + "(" + dc.upper() + ")")
        logger.info("Checking system resources for %s. please wait... ", dc.upper())
    perf = []
    for host in host_grp:
        host_connect(host[dc])
        zonecount = get_zone_count()
        loadvalue = (get_system_load("misc", "unix", "0", "system_misc") / 256.0)
        pagesize = get_system_load("kmem_cache", "unix", "0", "Memseg_cache")
        memvalue = int(get_system_load("pages", "unix", "0", "system_pages") * pagesize / 1024 / 1024)
        d = {'host': host[dc], 'loadavg15': loadvalue, 'freeMem': memvalue, 'zonecount': zonecount}
        if (memvalue < minmem or loadvalue > 30) and (args.listZones is None):
            logger.info("Host: %s, load-avg: %s, free-mem: %s, total-active zones: %s.", host[dc], '%.2f' % loadvalue, memvalue, zonecount)
            logger.info("Skipping host %s. CPU to high, or Memory to low.", host[dc])
        else:
            logger.info("Host: %s, load-avg: %s, free-mem: %s, total-active zones: %s.", host[dc], '%.2f' % loadvalue, memvalue, zonecount)
            perf.append(d)
        close_con()
    return perf


def gz_to_use(dc, host_grp):
    """Picks one Global Zone(system) to use.
    accepts: data center, host dictionary list.
    returns: single Global zone.
    """
    set_logging(dst_zone + "(" + dc.upper() + ")")
    logger.info("Verifying zone name is not in use, please wait...")
    for host in host_grp:
        logger.info("Checking Global Zone %s", host[dc])
        host_connect(host[dc])
        matchzone = verify_zone_exist()
        if matchzone is not None:
            close_con()
            logger.error("VM/Zone for %s exists with zone name %s on %s.", jiraid, matchzone, host[dc])
            print "\nERROR: VM/Zone for %s exists with the zone name %s on %s." % (jiraid, matchzone, host[dc])
            sys.exit(1)
        else:
            close_con()
    logger.info("Zone name for %s is not in use, continuing...", jiraid)
    logger.info("Evaluating system resources availability, Please wait...")
    perf = get_system_resources(dc, host_grp)

    # leastZones = min(perf, key=lambda x:x['zonecount'])
    # return  leastZones['host']
    leastLoad = min(perf, key=lambda x: x['loadavg15'])
    logger.info("Selecting Host: %s with load average of %s.", leastLoad['host'], '%.2f' % leastLoad['loadavg15'])
    return host['id'], leastLoad['host']

# ====================== End Global Zone Connection =====================

# =================== Get next avalable un-used port ====================


def missing_ports(num_list):
    """Verifies if port in use.
    accepts: port list
    returns: port number in a list format.
    """
    src_list = [x for x in range(low_port, num_list[-1] + 1)]
    num_list = set(num_list)
    if (list(num_list ^ set(src_list))):
        return (list(num_list ^ set(src_list)))
    else:
        return [src_list[-1]+1]


def get_zone_port(gz, zn):
    """Picks a zone service(SSH) port.
    accepts: global zone, non-global zone.
    returns: single port number.
    """
    db = pickledb.load('ports.db', False)
    try:
        db.dgetall(gz)
    except KeyError as error:
        db.dcreate(gz)
    if db.dexists(gz, zn):
        print db.dget(gz, zn)
        db.dadd(gz, (zn, db.dget(gz, zn)))
        db.dump()
        sys.exit(0)

    dbList = sorted(db.dvals(gz))
    if dbList:
        port = missing_ports(dbList)[0]
        db.dadd(gz, (zn, port))
        db.dump()
        return port
    else:
        db.dadd(gz, (zn, low_port))
        db.dump()
        return low_port


def del_zone_port(gz, zn):
    """Deletes / removes a zone service(SSH) port.
    accepts: global zone, non-global zone.
    """
    db = pickledb.load('ports.db', False)
    db.dpop(gz, zn)
    db.dump()

# =================== End Get next avalable port ========================


def verify_src_zone(src_zone, host):
    """Verify a source zone availability for cloning(installed mode).
    accepts: zone name, global zone name.
    returns: zone name.
    """
    host_connect(host)
    z1_list = rc.list_objects(
                  zonemgr.Zone(), radc.ADRGlobPattern({"name": src_zone})
                  )
    z1 = rc.get_object(z1_list[0])

    if z1.state == 'installed':
        logger.info("Zone %s is available(%s). continuing...", z1.name, z1.state)
        return z1
    else:
        close_con()
        logger.error("Source zone %s, Stat: %s, NOT available for cloning... exiting.", z1.name, z1.state)
        sys.exit(1)


def verify_dst_zone():

    """Verify a zone availability for cloning(configured mode).
    returns: zone RAD object.
    """
    logger.info("Configuring new zone: %s...", dst_zone),
    zonemanager = rc.get_object(zonemgr.ZoneManager())
    zonemanager.create(dst_zone, None, "SYSsolaris")

    z2_list = rc.list_objects(
                  zonemgr.Zone(), radc.ADRGlobPattern({"name": dst_zone})
                  )
    z2 = rc.get_object(z2_list[0])

    if z2.state == 'configured':
        logger.info("Configuring zone %s successful.", dst_zone)
        return z2
    else:
        close_con()
        logger.error("Destination zone %s is NOT available for cloning. zone stat is in %s... exiting.", z2.name, z2.stat)
        sys.exit(1)


def prep_zone(z2):
    """Set addineal zone properties.
    accepts: zone RAD object.
    """
    logger.info("Preparing zone %s. Setting zone properties...", z2.name),
    z2.editConfig()
    resource = zonemgr.Resource('global')
    prop1 = zonemgr.Property('autoboot', 'true')
    prop2 = zonemgr.Property('zonepath', '/zones/%{zonename}')
    z2.setResourceProperties(resource, [prop1])
    z2.setResourceProperties(resource, [prop2])
    z2.commitConfig()
    z2.editConfig()
    z2.setResourceProperties(
        zonemgr.Resource(
            'anet',
            [zonemgr.Property('linkname', 'net0')]
            ),
        [zonemgr.Property('lower-link', 'etherstub0')]
        )
    z2.commitConfig()
    logger.info("Successfully set zone %s properties.", z2.name)


def gen_sc_profile(zn, zp, host):
    """Generates a zone sc_profile xml format.
    accepts: zone name, zone port, global zone name.
    returns: sc_profile xml format.
    """
    d = {'node_name': zn, 'client_id': zp}
    s = """<?xml version="1.0" encoding="US-ASCII"?>
    <!DOCTYPE service_bundle SYSTEM "/usr/share/lib/xml/dtd/service_bundle.dtd.1">
    <!-- Auto-generated by sysconfig -->
    <service_bundle name="sysconfig" type="profile">
      <service name="system/identity" type="service" version="1">
        <instance enabled="true" name="cert"/>
        <instance enabled="true" name="node">
          <property_group name="config" type="application">
            <propval name="nodename" type="astring" value="{node_name}"/>
          </property_group>
        </instance>
      </service>
      <service name="system/name-service/cache" type="service" version="1">
        <instance enabled="true" name="default"/>
      </service>
      <service name="system/name-service/switch" type="service" version="1">
        <property_group name="config" type="application">
          <propval name="default" type="astring" value="files"/>
        </property_group>
        <instance enabled="true" name="default"/>
      </service>
      <service name="system/environment" type="service" version="1">
        <instance enabled="true" name="init">
          <property_group name="environment" type="application">
            <propval name="LANG" type="astring" value="en_US.ISO8859-1"/>
          </property_group>
        </instance>
      </service>
      <service name="system/timezone" type="service" version="1">
        <instance enabled="true" name="default">
          <property_group name="timezone" type="application">
            <propval name="localtime" type="astring" value="US/Eastern"/>
          </property_group>
        </instance>
      </service>
      <service name="system/config-user" type="service" version="1">
        <instance enabled="true" name="default">
          <property_group name="root_account" type="application">
            <propval name="password" type="astring" value="$5$jn8eXfiz$zqxHwPxBc0UHD2e0z34zMndm7G5ghtFBGoSklg7F8N4"/>
            <propval name="type" type="astring" value="role"/>
            <propval name="login" type="astring" value="root"/>
          </property_group>
          <property_group name="user_account" type="application">
            <propval name="roles" type="astring" value="root"/>
            <propval type="astring" name="shell" value="/usr/bin/bash"/>
            <propval type="astring" name="login" value="admin"/>
            <propval type="astring" name="password" value="$5$6wz1wkGt$RZ.PWs6xBiN2nMD4qJUlN9phcf2YuVE2i7HVOrYQib0"/>
            <propval type="astring" name="type" value="normal"/>
            <propval type="astring" name="sudoers" value="ALL=(ALL) ALL"/>
            <propval type="count" name="gid" value="10"/>
            <propval type="astring" name="description" value="Admin"/>
            <propval type="astring" name="profiles" value="System Administrator"/>
          </property_group>
        </instance>
      </service>
      <service name="network/ip-interface-management" type="service" version="1">
        <instance name="default" enabled="true">
          <property_group name="interfaces" type="application">
            <property_group name="lo0" type="interface-loopback">
              <property name="address-family" type="astring">
                <astring_list>
                  <value_node value="ipv4"/>
                  <value_node value="ipv6"/>
                </astring_list>
              </property>
              <property_group name="v4" type="address-static">
                <propval name="ipv4-address" type="astring" value="127.0.0.1"/>
                <propval name="prefixlen" type="count" value="8"/>
                <propval name="up" type="astring" value="yes"/>
              </property_group>
              <property_group name="v6" type="address-static">
                <propval name="ipv6-address" type="astring" value="::1"/>
                <propval name="prefixlen" type="count" value="128"/>
                <propval name="up" type="astring" value="yes"/>
              </property_group>
            </property_group>
            <property_group name="net0" type="interface-ip">
              <property name="address-family" type="astring">
                <astring_list>
                  <value_node value="ipv4"/>
                  <value_node value="ipv6"/>
                </astring_list>
              </property>
              <property_group name="v4" type="address-dhcp">
                <propval name="client-id" type="astring" value="{client_id}"/>
                <propval name="dhcp-wait" type="integer" value="-1"/>
                <propval name="primary-interface" type="boolean" value="false"/>
                <propval name="reqhost" type="astring" value=""/>
              </property_group>
              <property_group name="v6" type="address-addrconf">
                <propval name="interface-id" type="astring" value="::"/>
                <propval name="prefixlen" type="count" value="0"/>
                <propval name="stateful" type="astring" value="yes"/>
                <propval name="stateless" type="astring" value="yes"/>
              </property_group>
            </property_group>
          </property_group>
        </instance>
      </service>
    </service_bundle>"""
    sc_profile_loc = "/tmp/" + zn + "-sc_profile.xml"
    sc_profile = "echo '" + s.format(**d) + "' > " + sc_profile_loc
    cmd = radcon.build_ssh_cmd(host, "root", sc_profile)
    process = Popen(cmd, 0, None, PIPE, PIPE, preexec_fn=os.setsid)
    stdout, stderr = process.communicate()
    return sc_profile_loc


def clone_zone(z1, z2, host):

    """Clones source to destination zone.
    accepts: source zone name, destination zone name, global zone name.
    """
    logger.info("Generating zone port, used with SSH.")
    zonePort = get_zone_port(host, z2.name)
    logger.info("Generated %s as the zone SSH port.", zonePort)
    sc_profile = gen_sc_profile(z2.name, zonePort, host)
    options = ['-c', sc_profile]
    options.extend([z1.name])

    z2.clone(options=options)


def boot_zone(z2):

    """Boot a new created zone.
    accepts: zone RAD obejct.
    """
    if z2.state == 'installed':
        # Boot VM/Zone.
        logger.info("Booting VM/Zone %s for the first time. Please wait...", z2.name)
        z2_pat = radc.ADRGlobPattern({"name": z2.name})
        z2_boot = rc.get_object(zonemgr.Zone(), z2_pat)
        z2_boot.boot(None)
        logger.info("Successfully booted VM/Zone %s.", z2.name)
    else:
        logger.error("%s Faild to boot.", z2.name)


def connect_to_zone(z2):
    """connects / verifies the zone RAD is in ONLINE stat.
    accepts: zone RAD obejct.
    """
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

    network_instance = zcon.get_object(
                           smf.Instance(), radc.ADRGlobPattern(
                               {"service": "milestone/network",
                                "instance": "default"}
                               )
                           )

    while str(network_instance.state) != "ONLINE":
        logger.info("Waiting for network services to come ONLINE, curently %s.", network_instance.state)
        time.sleep(2)


def set_hostname(z2):

    """Sets the zone hostname.
    accepts: zone RAD obejct.
    """
    # services = zcon.list_objects(smf.Service())
    node_instance = zcon.get_object(
                        smf.Instance(), radc.ADRGlobPattern(
                            {"service": "system/identity",
                             "instance": "node"}
                            )
                        )
    logger.info("Network services are now ONLINE. continuing.")
    orig_type = node_instance.readProperty("config/nodename").type
    node_instance.writeProperty("config/nodename", orig_type, [z2.name])
    node_instance.writeProperty("config/loopback", orig_type, [z2.name])
    logger.info("Updating hostname to %s successful.", z2.name)


def enable_svc(z2, srvc, mount):
    """Enables an SMF service.
    accepts: zone RAD obejct, SMF instance name, SMF service name.
    """
    logger.info("Enabling service related to mount %s, in zone %s.", mount, z2.name)
    svc_instance = zcon.get_object(
                       smf.Instance(), radc.ADRGlobPattern(
                           {"service": "application/apps1_mount",
                            "instance": srvc}
                       )
                   )
    svc_instance.enable("")
    logger.info("Service enabled for %s mount. successful.", mount)


def disable_svc(z2, srvc, umountfs):
    """Disables an SMF service.
    accepts: zone RAD obejct, SMF instance name, SMF service name.
    """
    logger.info("Disableing service related to mount %s in zone %s.", umountfs, z2.name)
    svc_instance = zcon.get_object(
                       smf.Instance(), radc.ADRGlobPattern(
                           {"service": "application/apps1_mount",
                            "instance": srvc}
                       )
                   )
    svc_instance.disable("")
    logger.info("Service enabled for %s mount successful.", umountfs)


def chk_svc(z2, srvc):
    """Checks an SMF service state.
    accepts: zone RAD obejct, SMF instance name.
    returns: SMF service status
    """
    svc_instance = zcon.get_object(
                       smf.Instance(), radc.ADRGlobPattern(
                           {"service": "application/apps1_mount",
                            "instance": srvc}
                       )
                   )
    return (str(svc_instance.readProperty("config/sync_stat").values[0]))


def set_apps_mount(z2, srvc, mount):
    """Sets / updates a system mount point.
    accepts: zone RAD obejct, SMF instance name, mount point.
    """
    logger.info("Setting %s as /apps1_clone.", mount)
    mount_instance = zcon.get_object(
                         smf.Instance(), radc.ADRGlobPattern(
                             {"service": "application/apps1_mount",
                              "instance": srvc}
                         )
                     )
    mount_instance.writeProperty(
        "start/exec", smf.PropertyType.ASTRING,
        ['mount dc1nas2a-web:/export/' + mount + ' /apps1_clone'])

    logger.info("Successfully set %s as /apps1_clone mount.", mount)


def get_ip_port(z2, host):

    """Gets the local zone IP address and port number.
    accepts: zone RAD obejct, global zone name.
    prints: zone name, global zone, IP address, Port.
    """
    logger.info("Getting %s IP and Port information.", z2.name)
    getIp_instance = zcon.get_object(
                         smf.Instance(), radc.ADRGlobPattern(
                             {"service": "network/getIpPort",
                              "instance": "ip"}
                         )
                     )
    getIp_instance.refresh()
    ipAddr = getIp_instance.readProperty("config/ip_addr").values[0]
    ipPort = getIp_instance.readProperty("config/ip_port").values[0]
    logger.info("New VM/Zone is available on %s, with IP Address: %s Port %s", host, ipAddr, ipPort)
    print "------------------------------\nNew VM/Zone %s is available on %s with. \nIP Address: %s \nPort: %s\n------------------------------" % (z2.name, host, ipAddr, ipPort)


def display_img_stat(dc, host, dst_zone):

    """Displays zone related information.
    accepts: data center, global zone, zone name.
    prints: zone name, global zone, IP address, Port, mount point.
    """
    set_logging(dst_zone + "(" + dc.upper() + ")")
    logger.info("Pulling status...")
    print "Pulling status...\n------------------------------"
    print "Finding server containing zone for %s in %s." % (jiraid, dc.upper())
    logger.info("Finding server containing zone for %s.", jiraid)
    for host in host_grp:
        logger.info("Checking Global Zone %s.", host[dc])
        host_connect(host[dc])
        global matchzone
        matchzone = verify_zone_exist()
        if matchzone is not None:
            print "Found %s on %s in %s." % (jiraid, host[dc], dc.upper())
            logger.info("Found %s on %s.", jiraid, host[dc])
            break
        else:
            logger.info("No VM/Zone for %s on %s.", jiraid, host[dc])
    if matchzone is None:
        close_con()
        print "ERROR: Cannot find VM/Zone for %s on any of the servers in %s." % (jiraid, dc)
        logger.error("Cannot find VM/Zone for %s.", jiraid)
        sys.exit(1)

    snap = verif_snap("snap_" + matchzone)

    if (matchzone is None and snap != 200):
        close_con()
        print "ERROR: No VM/Zone %s or associated clone %s found." % (dst_zone, zfsdstsnap)
        sys.exit(1)
    else:

        z2_list = rc.list_objects(
                      zonemgr.Zone(), radc.ADRGlobPattern(
                          {"name": matchzone}
                          )
                      )
        z2 = rc.get_object(z2_list[0])

        if z2.state != 'running':
            close_con()
            logger.error("VM/Zone %s is not available, curent zone stat is %s.", matchzone, z2.state)
            print "VM/Zone %s is not available, curent zone stat is %s." % (matchzone, z2.state)
            sys.exit(0)
        else:
            connect_to_zone(z2)
            get_ip_port(z2, host[dc])
            close_con()
            print "Mount src: apps1_%s" % (matchzone)
            print "Mount dst: /apps1"


def rotate_img(dc, host, dst_zone):

    """Rotate / sync a zone source to destination mount point.
    accepts: data center, global zone, zone name.
    """
    set_logging(dst_zone + "(" + dc.upper() + ")")
    logger.info("Validating VM/Zone status.. please wait...")
    print "Finding server containing zone for %s in %s." % (jiraid, dc.upper())
    logger.info("Finding server containing zone for %s.", jiraid)
    for host in host_grp:
        logger.info("Checking Global Zone %s.", host[dc])
        host_connect(host[dc])
        global matchzone
        matchzone = verify_zone_exist()
        if matchzone is not None:
            print "Found %s on %s in %s." % (jiraid, host[dc], dc.upper())
            logger.info("Found %s on %s.", jiraid, host[dc])
            break
        else:
            logger.info("No VM/Zone for %s on %s.", jiraid, host[dc])
    if matchzone is None:
        close_con()
        print "ERROR: Cannot find VM/Zone for %s on any of the servers in %s." % (jiraid, dc)
        logger.error("Cannot find VM/Zone for %s.", jiraid)
        sys.exit(1)

    zfssrcsnap = "snap_" + matchzone
    zfssrcclone = "apps1_" + matchzone
    snap = verif_snap(zfssrcsnap)

    if (matchzone is None and snap != 200):
        close_con()
        print "ERROR: No VM/Zone %s or associated clone %s found." % (dst_zone, zfsdstsnap)
        sys.exit(1)
    else:
        logger.info("Rotating /apps1(%s) in zone %s...", zfssrcclone, matchzone)
        print "(%s)Rotating /apps1(%s) in zone %s.. please wait..." % (dc.upper(), zfssrcclone, matchzone)
        z2_list = rc.list_objects(
                      zonemgr.Zone(), radc.ADRGlobPattern(
                          {"name": matchzone}
                          )
                      )
        z2 = rc.get_object(z2_list[0])

        if z2.state != 'running':
            close_con()
            logger.error("VM/Zone %s is not available, curent zone stat is %s.", matchzone, z2.state)
            print "VM/Zone %s is not available, curent zone stat is %s." % (matchzone, z2.state)
            sys.exit(0)
        else:
            connect_to_zone(z2)

    if dc == "ha":
        # Create ZFS snap.
        logger.info("Cerating snapshot: %s", zfsdstsnap)
        snap = create_snap(zfsdstsnap)
        if snap == 201:
            logger.info("Snapshot created successfully.")
        else:
            close_con()
            logger.error("Snapshot %s creation failed, with error code: %s. exiting.", zfsdstsnap, snap)
            print("Snapshot %s creation failed, with error code: %s \nExiting.") % (zfsdstsnap, snap)
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
            close_con()
            logger.error("Clone %s creation failed. Return error code is: %s. exiting.",  zfsdstclone, clone)
            print("Clone %s creation failed. Return error code is: %s \nExiting.") % (zfsdstclone, clone)
            sys.exit(1)

        # Mount new apps1 clone as /apps1_clone
        set_apps_mount(z2, "apps1dst", zfsdstclone)
        enable_svc(z2, "apps1dst", zfsdstclone)

        # Run rsync
        enable_svc(z2, "apps1sync", "rsync")
        time.sleep(1)

        while True:
            sync_stat = chk_svc(z2, "apps1sync")
            if sync_stat == "running":
                logger.info("Sync to /apps1_clone(%s) is still in progress.", zfsdstclone)
                time.sleep(10)
            elif sync_stat == "initial":
                close_con()
                logger.error("Sync to %s never started, the return code is: %s", zfsdstclone, sync_stat)
                sys.exit(1)
            elif sync_stat == "completed":
                disable_svc(z2, "apps1sync", "NA")
                logger.info("Sync to /apps1_clone(%s) completed sucssfuly.", zfsdstclone)
                break
            else:
                close_con()
                logger.error("An error occurred while trying to sync %s, with error code: (%s)", zfsdstclone, sync_stat)
                sys.exit(1)

        disable_svc(z2, "apps1sync", "rsync")

        # Umount /apps1 and /apps1_clone
        disable_svc(z2, "apps1dst", zfsdstclone)
        disable_svc(z2, "apps1src", zfssrcclone)

        # Rename snap, clone orignal apps-time => apps1-newtime
        rename_snap(zfssrcsnap, zfssrcsnap + "-" + dt.strftime("%s"))
        rename_clone(zfssrcclone, zfssrcclone + "-" + dt.strftime("%s"))

        # Rename snap, clone orignal apps-time => apps1-newtime
        rename_snap(zfsdstsnap, zfssrcsnap)
        rename_clone(zfsdstclone, zfssrcclone)

        # Mount new clone as /apps1
        enable_svc(z2, "apps1src", zfssrcclone)
        close_con()
        logger.info("Rotation of /apps1(%s) in zone %s completed successfully.", zfssrcclone, matchzone)
        print "(%s)Rotation of /apps1(%s) in zone %s completed successfully." % (dc.upper(), zfssrcclone, matchzone)
    else:
        disable_svc(z2, "apps1src", zfssrcclone)
        enable_svc(z2, "apps1src", zfssrcclone)
        close_con()
        logger.info("Rotation of /apps1(%s) in zone %s completed successfully.", zfssrcclone, matchzone)
        print "(%s)Rotation of /apps1(%s) in zone %s completed successfully." % (dc.upper(), zfssrcclone, matchzone)

# ********************** Main calls ********************** #


def clone_vm_fs(dc, host):

    """Clone zone and file system - source to destination.
    accepts: data center, global zone.
    """
    if dc == "dr":
        set_logging(dst_zone + "(" + dc.upper() + ")")
    if dc == "ha":
        print "Cloning VM/Zone %s and associated file systems\nProgress is being logged to %s\n--------------------------------" % (dst_zone, log_output)
        logger.info('Validating configuration request.')
        snap = verif_snap(zfsdstsnap)
        if snap == 200:
            close_con()
            print "Snapshot %s exists. Error code: %s  \nExiting." % (zfsdstsnap, snap)
            logger.error("Snapshot %s exists. Error code: %s  exiting.", zfsdstsnap, snap)
            sys.exit(snap)
        else:
            logger.info("Snapshot %s is valid. continuing...", zfsdstsnap)

        clone = verif_clone(zfsdstsnap, zfsdstclone)
        if clone == 200:
            close_con()
            print "Clone %s exists. Error code: %s \nExiting." % (zfsdstclone)
            logger.error("Clone %s exists. Error code: %s exiting.", zfsdstclone, clone)
            sys.exit(snap)
        else:
            logger.info("Clone %s is valid. continuing...", zfsdstclone)

    # Checking source zone availability.
    logger.info("Checking source zone availability...")
    src_z = verify_src_zone(src_zone, host)

    # Configuring destination zone.
    dst_z = verify_dst_zone()
    logger.info("All checks in %s passed, continuing.", dc)
    prep_zone(dst_z)

    if dc == "ha":
        # Create ZFS snap.
        logger.info("Cerating snapshot: %s", zfsdstsnap)
        snap = create_snap(zfsdstsnap)
        if snap == 201:
            logger.info("Snapshot created successfully.")
        else:
            close_con()
            logger.error("Snapshot %s creation failed, with error code: %s. exiting.", zfsdstsnap, snap)
            print("Snapshot %s creation failed, with error code: %s \nExiting.") % (zfsdstsnap, snap)
            sys.exit(snap)

        # Verifying ZFS snap availability.
        logger.info("Verifying snapshot availability.")
        snap = verif_snap(zfsdstsnap)
        if snap == 200:
            logger.info("Snapshot %s available. continuing...", zfsdstsnap)
        else:
            close_con()
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
            close_con()
            print("Clone %s creation failed. Return error code is: %s \nExiting.") % (zfsdstclone, clone)
            sys.exit(1)

    # Clone source to destination zone.
    logger.info("CLONING VM/Zone")
    logger.info("Source zone: %s", src_z.name)
    logger.info("Destination zone: %s", dst_z.name)
    logger.info("Please wait...")
    clone_zone(src_z, dst_z, host)
    logger.info("Successfully created zone %s", dst_z.name)

    # Boot zone.
    boot_zone(dst_z)

    # ---===== Prep zone =====----
    #
    # Check for zone availability.
    connect_to_zone(dst_z)
    # Set zone hostname.
    # set_hostname(dst_z)
    # Set zone hostname.
    enable_svc(dst_z, "apps1src", "/apps1")
    # Get zone IP adn Port.
    get_ip_port(dst_z, host)
    # Close connection.
    close_con()

    logger.info("Installation of zone %s in %s successfully completed.", dst_z.name, dc.upper())
    print "Installation of zone %s in %s successfully completed." % (dst_z.name, dc.upper())


def delete_filesystem():

    """Deletes a ZFS file system."""
    logger.info("Deleting clone/snapshots related to zone: %s", matchzone)
    for snap in get_snap_list('snap_' + matchzone):
        logger.info("Snap %s related to zone %s, will be deleted.", snap, matchzone)
        delete_clone = delete_snap(snap)
        if delete_clone == 204:
            close_con()
            logger.info("Clone/snapshot apps1_%s and associated snap_%s deleted successfully.", snap, snap)
        else:
            close_con()
            print("ERROR: Clone snap_%s deletion failed. Return error code is: %s \nExiting.") % (snap, delete_clone)
            sys.exit(1)
    logger.info("Uninstall/delete of VM/Zone %s completed successfully.", matchzone)
    print "Uninstall/delete completed successfully."


def delete_vm(dc, host_grp):

    """Deletes a VM/Zone file system.
    accepts: Data center, dictionary of hosts.
    """
    set_logging(dst_zone + "(" + dc.upper() + ")")
    print "Finding server containing zone for %s in %s." % (jiraid, dc.upper())
    logger.info("Finding server containing zone for %s in %s.", jiraid, dc.upper())
    for host in host_grp:
        logger.info("Checking Global Zone %s.", host[dc])
        host_connect(host[dc])
        global matchzone
        matchzone = verify_zone_exist()
        if matchzone is not None:
            print "Found %s on %s in %s." % (jiraid, host[dc], dc)
            logger.info("Found %s on %s.", jiraid, host[dc])
            break
        else:
            logger.info("No VM/Zone for %s on %s.", jiraid, host[dc])
    if matchzone is None:
        close_con()
        print "ERROR: Cannot find VM/Zone for %s on any of the servers in %s." % (jiraid, dc)
        logger.error("Cannot find VM/Zone for %s.", jiraid)
        sys.exit(1)

    print "Deleting VM/Zone %s and associated snap_%s on %s.\nProgress is being logged in %s\n--------------------------------" % (matchzone, matchzone, host[dc], log_output)
    logger.info("Deleting VM/Zone %s on %s.", matchzone, host[dc])

    z2_list = rc.list_objects(
                  zonemgr.Zone(), radc.ADRGlobPattern(
                      {"name": matchzone}
                      )
                  )
    if not z2_list:
        close_con()
        print "ERROR: VM/Zone does not exist, please verify the spelling is correct."
        sys.exit(1)

    z2 = rc.get_object(z2_list[0])

    logger.info("Preparing removal of %s.", matchzone)
    if z2.state == "running":
        logger.info("Halting %s, please wait...", matchzone)
        z2.halt(None)
        logger.info("Halting %s completed successfully.", matchzone)
        logger.info("Uninstalling %s please wait...", matchzone)
        z2.uninstall(['-F'])
        logger.info("Uninstalling %s completed successfully.", matchzone)
    elif z2.state == "incomplete":
        logger.info("Uninstalling %s please wait...", matchzone)
        z2.uninstall(['-F'])
        logger.info("Uninstalling %s completed successfully.", matchzone)
    else:
        logger.info("Uninstall not required for zone %s in state %s.", z2.name, z2.state)
    logger.info("Deleteing %s please wait...", z2.name)
    delete_zone = rc.get_object(zonemgr.ZoneManager())
    delete_zone.delete(z2.name)
    close_con()
    logger.info("Deleteing configuration of %s completed successfully.", matchzone)

    logger.info("Removing zone SSH port mapping configuration.")
    del_zone_port(host[dc], matchzone)
    logger.info("Zone SSH port mapping removed successfully.")
    if dc == "ha":
        delete_filesystem()
    logger.info("Removel of zone %s completed successfully.", matchzone)


if __name__ == "__main__":

    if args.listZones is not None:
        print "Checking system resources. please wait...\n"
        for dc in dclist:
            host_grp = dc_host_list(hostdclist, dc)
            main(dc, host_grp)
        sys.exit(0)
    if drstat == "both":
        for dc in dclist:
            if dc == "ha":
                host_grp = dc_host_list(hostdclist, dc)
                if args.delete or args.imgStat or args.rotateImg:
                    main(dc, host_grp)
                else:
                    print "Evaluating system resources availability. Please wait..."
                    hid, host = gz_to_use(dc, host_grp)
                    main(dc, host_grp[hid-1]['ha'])
            else:
                host_grp = dc_host_list(hostdclist, dc)
                if args.delete or args.imgStat or args.rotateImg:
                    main(dc, host_grp)
                else:
                    main(dc, host_grp[hid-1]['dr'])
