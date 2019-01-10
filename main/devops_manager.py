#!/usr/bin/env python
#title           :clone_zfs.py
#description     :Creating a DevOps like on Solaris
#author          :Eli Kleinman
#release date    :20181018
#update date     :20190110
#version         :0.7
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
import configparser
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
group1.add_argument('-r', '--rotateImg', default=False, type=str,
                    choices=['app', 'db'],
                    help='rotate / sync update /apps1 or refresh /ifxsrv in a VM/zone.')

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


def get_config(section, item=None, zone_name=None, item_type=None, dc=None):
    config = configparser.ConfigParser()
    config.sections()
    config.read('devops_config.ini')
    config_details = dict(config.items(section))
    val_list = []
    val_dict = {}
    rec = 0
    if section == "ZFS_DST_SNAP":
        return str(config_details[item]) + zone_name
    elif item == "DICT_LIST":
        for key, val in config.items(section):
            if key.split(".")[2] == "1":
                rec = str(key.split(".")[1])
                file_name = str(val)
            elif key.split(".")[2] == "2":
                dst_file = str(val)
            else:
                if item_type == "link":
                    dst_data = str(val)
                else:
                    dst_data = str(get_file_data(dst_file), dc)
                d = {"file": file_name, "src_file": str(dst_file), "dst_val": dst_data}
                val_dict[rec] = d
        return val_dict
    elif section == "HOST_LIST":
        for key, val in config.items('HOST_LIST'):
            if key.split(".")[0] == "ha":
                rec += 1
                hahost = str(key.split(".")[0])
                haval = str(val)
                d = {'id': rec,  hahost: haval}
            else:
                drhost = str(key.split(".")[0])
                drval = str(val)
                d[drhost] = str(drval)
                val_list.append(d)
        return val_list
    elif item == "ITEM_LIST":
        for key, val in config.items(section):
            if zone_name:
                val_list.append(str(val) + str(zone_name))
            else:
                val_list.append(str(val))
        return val_list
    else:
        return str(config_details[item])


def get_file_data(src, dc):
    try:
        f = open(src, "r")
    except IOError, e:
        print dc.upper(), e
        logger.error("%s", e)
        logger.error("%s", sys.exc_type)
        sys.exit(1)
    data = f.read()
    f.close()
    return data


# ====================== ZFS related ======================

# Set system proxy

if get_config('PROXY', 'http_proxy') != "None":
    os.environ['http_proxy'] = get_config('PROXY', 'http_proxy')
if get_config('PROXY', 'https_proxy') != "None":
    os.environ['https_proxy'] = get_config('PROXY', 'https_proxy')

# ZFSSA API URL
url = get_config('ZFSSA', 'url')

# ZFSSA API login
zfsuser = get_config('ZFSSA', 'zfsuser')
zfspass = get_config('ZFSSA', 'zfspass')
zfsauth = (zfsuser, zfspass)

# ZFS pool
zfspool = get_config('ZFSSA', 'zfspool')

# ZFS project
zfsproject = get_config('ZFSSA', 'zfsproject')

# ZFS source filesystem
zfssrcfslist = get_config('ZFS_SRC_FS', 'ITEM_LIST')

# ZFS snap filesystem
zfsdstsnap = get_config('ZFS_DST_SNAP', 'zfsdstsnap', dst_zone)

# ZFS clone filesystem(s)
zfsdstclonelist = get_config('ZFS_DST_FS', 'ITEM_LIST', dst_zone)

# Headers
jsonheader = {'Content-Type': 'application/json'}

# ====================== Global and Zone related =================

# Global zone - will the one with the lowest CPU load.
# Define dr state, can be ha, dr or both.
dclist = ['ha', 'dr']
drstat = 'both'

# Define a list of Global Zone set of HA and DR.
hostdclist = get_config('HOST_LIST')

# Min Load and Memory required for Global Zones
loadvalue = int(get_config('CONFIG', 'loadvalue'))
minmem = int(get_config('CONFIG', 'minmem'))

# Lowest / first port used for connections - firewall mapping
low_port = int(get_config('CONFIG', 'low_port'))

# Source zone
src_zone = get_config('CONFIG', 'src_zone')

# Dest (Jira) zone name
jiraid = args.jiraid

# NFS services to started
nfs_services = [
    'network/nfs/fedfs-client',
    'network/nfs/cleanup-upgrade',
    'network/nfs/cleanup',
    'network/nfs/cbd',
    'network/nfs/mapid',
    'network/nfs/nlockmgr',
    'network/nfs/status',
    'network/nfs/rquota',
    'network/nfs/client'
    ]

# LDAP certficate list
if get_config('LDAP', 'ldap') == "yes":
    cert_list = get_config('LDAP_CERTS', 'ITEM_LIST')

# Sc Profile xml to use
sc_profile_templ = get_config('CONFIG', 'sc_profile')

# ====================== End of settings ======================


# ====================== Main call ===========================


def main(dc, host, drhost):
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
        if dc == "ha":
            clone_fs(dc, host, dst_zone, drhost)
        p = Process(target=clone_vm, args=(dc, host,))
        p.start()

# ====================== ZFSSA Reset Calls ===========================


def verif_snap(zfsdstsnap, zfssrcfs):
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


def create_snap(zfsdstsnap, zfssrcfs):
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


def rename_snap(zfssrcsnap, zfsdstsnap, zfssrcfs):
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


def create_clone(zfsdstsnap, zfsdstclone, zfssrcfs):
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


def get_snap_list(zone, zfssrcfs):
    """Gather list of ZFS clone/snapshots related to a Zone.
    accepts: the exsistng Zone name.
    returns: list of ZFS clone/snapshots.
    """
    logger.info("Searching for snaps related to zone %s for %s", zone, zfssrcfs)
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
    logger.info("Found %s snap/clones related to zone %s for %s.", len(snaplist), zone, zfssrcfs)
    return snaplist


def delete_snap(zfsdstsnap, zfssrcfs):
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
            z_run.append(zl.name)
    return z_run


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


def verify_zone_exist(zone_name):
    """Verifies / checks if a zone name exist.
    returns: the zone name.
    """
    zones = rc.list_objects(zonemgr.Zone())
    for i in range(0, len(zones)):
        zone = rc.get_object(zones[i])
        if re.search(zone_name, zone.name):
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
        if args.listZones is not None:
            zone_list = get_zone_count()
            zonecount = len(zone_list)
        else:
            zonecount = len(get_zone_count())
        loadvalue = (get_system_load("misc", "unix", "0", "system_misc") / 256.0)
        pagesize = get_system_load("kmem_cache", "unix", "0", "Memseg_cache")
        memvalue = int(get_system_load("pages", "unix", "0", "system_pages") * pagesize / 1024 / 1024)
        if args.listZones is not None:
            d = {
                'ID': host['id'], 'Hostname': host[dc],
                '15 minute load average': '%.2f' % loadvalue, 'Free memory': '%s Mb' % memvalue,
                'Zone count': zonecount, 'Active zones': zone_list,
                }
        else:
            d = {
                'id': host['id'], 'host': host[dc],
                'loadavg15': loadvalue, 'freeMem': memvalue,
                'zonecount': zonecount
                }
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
        matchzone = verify_zone_exist("-" + jiraid + "$")
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
    return leastLoad['id'], leastLoad['host']

# ====================== End Global Zone Connection =====================

# =================== Get next avalable un-used port ====================


def missing_ports(num_list):
    """Verifies if port in use.
    accepts: port list
    returns: port number in a list format.
    """
    src_list = [x for x in range(int(low_port), num_list[-1] + 1)]
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
    try:
        db.dpop(gz, zn)
    except KeyError as e:
        logger.error("Port/Key not found: %s", e)
        logger.error("%s", sys.exc_type)
    db.dump()

# =================== End Get next avalable port ========================


def create_src_zone_manifest(z1, host):
    logger.info("Creating %s with port %s as the zone SSH port.", z1.name, 31005)
    src = '/usr/share/auto_install/manifest/zone_default.xml'
    dst = '/tmp/z-source.xml'
    f = open(src, "r")
    data = f.read()
    f.close()
    pkg_src = "</name>"
    git_kg = "</name>\n                <name>pkg:/developer/versioning/git</name>\n</name>\n                <name>pkg:/package/svr4</name>"
    newdata = data.replace(pkg_src, git_kg)
    sc_profile_loc = run_remote_cmd(z1.name, 31005, host, "/tmp/", newdata, "-manifest.xml")
    logger.info("Generated %s as the zone SSH port.", 31005)
    return sc_profile_loc


def verify_src_zone(src_zone, host):
    """Verify a source zone availability for cloning(installed mode).
    accepts: zone name, global zone name.
    returns: zone name.
    """
    z1_list = rc.list_objects(
                  zonemgr.Zone(), radc.ADRGlobPattern({"name": src_zone})
                  )
    z1 = rc.get_object(z1_list[0])

    if z1.state == 'installed':
        logger.info("Zone %s is available(%s). continuing...", z1.name, z1.state)
        return z1
    else:
        close_con()
        logger.error("Source zone %s on %s, Stat: %s, NOT available for cloning... exiting.", z1.name, host, z1.state)
        print("Source zone %s on %s, Stat: %s, NOT available for cloning... exiting.") % (z1.name, host, z1.state)
        sys.exit(1)


def create_src_zone_service(z1, host):
    logger.info("Creating services, please wait...")
    zone_path = '/zones/z-source/root/'
    if get_config('DIR', 'dir') == "yes":
        dir_list = get_config('DIR_LIST', 'ITEM_LIST')
        for i in dir_list:
            remote_results = run_remote_cmd(z1.name, 31005, host, zone_path + i, None, None)
            logger.info("Successfully created the directory %s ", (zone_path + i))

    if get_config('SMF_PROFILE', 'start') == "yes":
        smf_svc_list = get_config('SMF_PROFILE_LOC', 'DICT_LIST')
        for i in smf_svc_list.iteritems():
            for key, value in i[1].iteritems():
                if key == "file":
                    svc_path = zone_path + 'lib/svc/manifest/site/'
                    svc_file = value
                elif key == "dst_val":
                    svc_value = value
            remote_results = run_remote_cmd(z1.name, 31005, host, svc_path, svc_value, svc_file)
            logger.info("Successfully created the file %s%s ", svc_path, z1.name + svc_file)

    if get_config('STARTUP', 'start') == "yes":
        startup_list = get_config('STARTUP_SCRIPTS', 'DICT_LIST')

        for i in startup_list.iteritems():
            for key, value in i[1].iteritems():
                if key == "file":
                    svc_path = zone_path + 'opt/cloneFiles/bin/'
                    svc_file = value
                elif key == "dst_val":
                    svc_value = value
            # Create files
            remote_results = run_remote_cmd(z1.name, None, host, svc_path, svc_value, svc_file)
            logger.info("Successfully created the file %s%s", svc_path, svc_file)
            # Set exec bit on files
            remote_results = run_remote_cmd(z1.name, None, host, svc_path, "chmod", svc_file)
            logger.info("Successfully set execution of the file %s%s", svc_path, svc_file)

    # Add NFS mounts to /etc/vfstab
    if get_config('NFS', 'nfs') == "yes":
        vfstab_data = """#\n## NFS mounts\n"""
        vfstab_list = get_config('NFS_MOUNTS', 'ITEM_LIST')
        for fs in vfstab_list:
            vfstab_data += fs + '\n'
        remote_results = run_remote_cmd(z1.name, None, host, "/etc/", vfstab_data, "vfstab")

    # Add LD_LIBRARY_PATH to /etc/profile
    if get_config('OTHER', 'etc_profile') != "None":
        etc_profile = get_config('OTHER', 'etc_profile')
        remote_results = run_remote_cmd(z1.name, None, host, "/etc/", etc_profile, "profile")

    # Add db shared memory config to /etc/project
    if get_config('OTHER', 'etc_user_attr') != "None":
        etc_user_attr = get_config('OTHER', 'etc_user_attr')

    # Link /usr/informix > /apps1/informix
    if get_config('LINK', 'link') == "yes":
        link_list = get_config('LINK_LIST', 'DICT_LIST', None, 'link', dc)
        for i in link_list.iteritems():
            for key, value in i[1].iteritems():
                if key == "dst_val":
                    dst_link = value
                elif key == "src_file":
                    src_link = value
            remote_results = run_remote_cmd(z1.name, None, host, src_link, "link", dst_link)


def enable_src_zone_nfs(dst_z, host):
    for service in nfs_services:
        service_action(dst_z, service, "default", "enable")


def create_dst_zone(zone_name):

    """Verify a zone availability for cloning(configured mode).
    returns: zone RAD object.
    """
    logger.info("Configuring new zone: %s...", zone_name),
    zonemanager = rc.get_object(zonemgr.ZoneManager())
    zonemanager.create(zone_name, None, "SYSsolaris")

    z2_list = rc.list_objects(
                  zonemgr.Zone(), radc.ADRGlobPattern({"name": zone_name})
                  )
    z2 = rc.get_object(z2_list[0])

    if z2.state == 'configured':
        logger.info("Configuring zone %s successful.", zone_name)
        return z2
    else:
        close_con()
        logger.error("Destination zone %s is NOT available for cloning. zone stat is in %s... exiting.", z2.name, z2.stat)
        print("Destination zone %s is NOT available for cloning. zone stat is in %s... exiting.") % (z2.name, z2.stat)
        sys.exit(1)


def prep_zone(z2):
    """Set addineal zone properties.
    accepts: zone RAD object.
    """
    logger.info("Preparing zone %s. Setting zone properties...", z2.name),
    z2.editConfig()
    resource = zonemgr.Resource('global')
    if z2.name != "z-source":
        prop1 = zonemgr.Property('autoboot', 'true')
    prop2 = zonemgr.Property('zonepath', '/zones/%{zonename}')
    if z2.name != "z-source":
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


def run_remote_cmd(zn, zp, host, dir_loc, file_data, file_type):
    """Generates remote file data e.g. a zone sc_profile xml, etc..
    accepts: zone name, zone port, global zone name, directory location, file data, file type e.g. xml.
    returns: directory/file location.
    """
    if file_data is None:
        build_cmd = "mkdir -p " + dir_loc
        file_loc = None
    elif file_data is "chmod":
        build_cmd = "chmod +x " + dir_loc + file_type
        file_loc = None
    elif file_data is "link":
        build_cmd = "ln -s " + dir_loc + " " + file_type
        file_loc = None
    else:
        if re.search("dc2", host):
            profile_name = "nyi_oud_ldap-ext_636"
            profile_ip = "10.50.22.235:1389"
        else:
            profile_name = "dc1_oud_ldap-ext_636"
            profile_ip = "10.150.22.51:1389"
        d = {'node_name': zn, 'client_id': zp, 'profile_name': profile_name,
             'profile_ip': profile_ip, 'NS1': '{NS1}'}
        file_loc = dir_loc + zn + file_type
        if zp is None:
            build_cmd = "echo '" + file_data + "' > " + dir_loc + file_type
        else:
            build_cmd = "echo '" + file_data.format(**d) + "' > " + file_loc

    cmd = radcon.build_ssh_cmd(host, "confmgr", build_cmd)
    cmd.insert(-2, '-o')
    cmd.insert(-2, 'StrictHostKeyChecking=no')
    process = Popen(cmd, 0, None, PIPE, PIPE, preexec_fn=os.setsid)
    stdout, stderr = process.communicate()
    if stdout:
        print stdout
    if stderr:
        print stderr
    return file_loc


def install_src_zone(z1, host, profile_loc, manifest_loc):

    """Clones source to destination zone.
    accepts: source zone name, destination zone name, global zone name.
    """
    logger.info("INSTALLING VM/Zone, this can take a while, Please wait...")
    options = ['-m', manifest_loc, '-c', profile_loc]
    if z1.name != "z-source":
        options.extend([z1.name])

    z1.install(options=options)
    logger.info("Successfully installed zone %s on %s", z1.name, host)


def clone_zone(z1, z2, host, dc):

    """Clones source to destination zone.
    accepts: source zone name, destination zone name, global zone name.
    """
    logger.info("Generating zone port, used with SSH.")
    zonePort = get_zone_port(host, z2.name)
    logger.info("Generated %s as the zone SSH port.", zonePort)
    sc_profile = run_remote_cmd(z2.name, zonePort, host, "/tmp/", str(get_file_data("conf/" + sc_profile_templ, dc)), "-sc_profile.xml")
    options = ['-c', sc_profile]
    options.extend([z1.name])

    z2.clone(options=options)
    return zonePort


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


def connect_to_zone(z2, user):
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
            zcon = radcon.connect_zone(rc, z2.name, user)
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


def service_action(z2, srvc, inst, action, mount=None):
    """Take action with an SMF service, action is one of: enable, disable, restart.
    accepts: zone RAD obejct, SMF instance name, SMF service name.
    returns: if, SMF property value.
    prints: zone name, global zone, IP address, Port.
    """
    logger.info("%s for service %s:%s in zone %s.", action, srvc, inst, z2.name)
    svc_instance = zcon.get_object(
                       smf.Instance(), radc.ADRGlobPattern(
                           {"service": srvc,
                            "instance": inst}
                       )
                   )
    if action == "get_prop":
        if inst == "apps1sync":
            return (str(svc_instance.readProperty("config/sync_stat").values[0]))
        if inst == "ip":
            svc_instance.refresh()
            ipAddr = svc_instance.readProperty("config/ip_addr").values[0]
            ipPort = svc_instance.readProperty("config/ip_port").values[0]
            return ipAddr, ipPort
    elif action == "set_prop":
        svc_instance.writeProperty(
            "start/exec", smf.PropertyType.ASTRING,
            ['mount -o vers=3 nas-devops:/export/' + mount + ' /apps1_clone'])
    elif ((action == "enable") or (action == "disable")):
        getattr(svc_instance, action)("")
    else:
        getattr(svc_instance, action)()
    logger.info("service %s for %s:%s. successful.", action, srvc, inst)


def display_img_stat(dc, host, dst_zone):

    """Displays zone related information.
    accepts: data center, global zone, zone name.
    prints: zone name, global zone, IP address, Port, mount point.
    """
    set_logging(dst_zone + "(" + dc.upper() + ")")
    logger.info("Verifying status...")
    print "Pulling status...\n------------------------------"
    print "Finding server containing zone for %s in %s." % (jiraid, dc.upper())
    logger.info("Finding server containing zone for %s.", jiraid)
    for host in host_grp:
        logger.info("Checking Global Zone %s.", host[dc])
        host_connect(host[dc])
        global matchzone
        matchzone = verify_zone_exist("-" + jiraid + "$")
        if matchzone is not None:
            print "Found %s on %s in %s." % (jiraid, host[dc], dc.upper())
            logger.info("Found %s on %s.", jiraid, host[dc])
            break
        else:
            logger.info("No VM/Zone for %s on %s.", jiraid, host[dc])
    if matchzone is None:
        close_con()
        print "ERROR: Cannot find VM/Zone for %s on any of the servers in %s." % (jiraid, dc.upper())
        logger.error("Cannot find VM/Zone for %s.", jiraid)
        sys.exit(1)

    snap = verif_snap("snap_" + matchzone, zfssrcfslist[0])

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
            connect_to_zone(z2, "confmgr")
            ipAddr, ipPort = service_action(z2, "network/getIpPort", "ip", "get_prop")
            if dc == "ha":
                logger.info("******* Informix Database is only running in %s *******", host[dc])
                print("===============================================================")
                print("******* NOTE: Informix is only running on %s *******") % (host[dc])
                print("                         (%s)                       ") % (host[dc].split("-")[1])
                print("===============================================================")
                logger.info("New VM/Zone is available on %s, with IP Address: %s Port %s", host[dc], ipAddr, ipPort)
                print "\n-------========= Active data center =========------- \n        VM/Zone Name: %s \n        Hostname: %s \n        Zone Port: %s \n        DB Port: %s \n        Internal IP Address: %s" % (z2.name, host[dc].split("-")[1], ipPort, int(ipPort) + 500, ipAddr)
            else:
                print "\n-------========= Standby data center =========------- \n        VM/Zone Name: %s \n        Hostname: %s \n        Zone Port: %s \n        DB Port: %s \n        Internal IP Address: %s" % (z2.name, host[dc], ipPort, int(ipPort) + 500, ipAddr)
            close_con()
            print "        VM Mount source: apps1_%s" % (matchzone)
            print "        DB Mount source: ifxdb-do_%s" % (matchzone)
            print "        VM Mount destination: /apps1"
            print "        DB Mount destination: /ifxsrv"


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
        matchzone = verify_zone_exist("-" + jiraid + "$")
        if matchzone is not None:
            print "Found %s on %s in %s." % (jiraid, host[dc], dc.upper())
            logger.info("Found %s on %s.", jiraid, host[dc])
            break
        else:
            logger.info("No VM/Zone for %s on %s.", jiraid, host[dc])
    if matchzone is None:
        close_con()
        print "ERROR: Cannot find VM/Zone for %s on any of the servers in %s." % (jiraid, dc.upper())
        logger.error("Cannot find VM/Zone for %s.", jiraid)
        sys.exit(1)

    zfssrcsnap = "snap_" + matchzone
    if args.rotateImg == "app":
        zfssrcclone = "apps1_" + matchzone
        zfsdstclone = "apps1_" + dst_zone
        zfssrcfs = "apps1-prod"
        zfsmount = "/apps1"
    else:
        zfssrcclone = "ifxdb-do_" + matchzone
        zfsdstclone = "ifxdb-do_" + dst_zone
        zfssrcfs = "ifxdb-do"
        zfsmount = "/ifxsrv"
    snap = verif_snap(zfssrcsnap, zfssrcfs)

    if (matchzone is None and snap != 200):
        close_con()
        print "ERROR: No VM/Zone %s or associated clone %s found." % (dst_zone, zfsdstsnap)
        sys.exit(1)
    else:
        if dc == "ha":
            logger.info("Rotating %s(%s) mount in zone %s...", zfsmount, zfssrcclone, matchzone)
            print "(%s)Rotating %s(%s) mount in zone %s.. please wait..." % (zfsmount, dc.upper(), zfssrcclone, matchzone)
        else:
            logger.info("Re-mounting %s(%s) mount in zone %s...", zfsmount, zfssrcclone, matchzone)
            print "(%s)Re-mounting %s(%s) mount in zone %s.. please wait..." % (zfsmount, dc.upper(), zfssrcclone, matchzone)

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
            connect_to_zone(z2, "confmgr")

    if dc == "ha":
        # Create ZFS snap.
        logger.info("Cerating snapshot: %s for %s", zfsdstsnap, zfssrcfs)
        snap = create_snap(zfsdstsnap, zfssrcfs)
        if snap == 201:
            logger.info("Snapshot %s created successfully.", zfsdstsnap)
        else:
            close_con()
            logger.error("Snapshot %s creation failed, with error code: %s. exiting.", zfsdstsnap, snap)
            print("Snapshot %s creation failed, with error code: %s \nExiting.") % (zfsdstsnap, snap)
            sys.exit(snap)

        # Cloning file-systems.
        logger.info("CLONING file-systems")
        logger.info("Source: %s", zfssrcfs)
        logger.info("Destination: %s",  zfsdstclone)
        logger.info("Please wait...")
        clone = create_clone(zfsdstsnap, zfsdstclone, zfssrcfs)
        if clone == 201:
            logger.info("Successfully created clone %s",  zfsdstclone)
        else:
            close_con()
            logger.error("Clone %s creation failed. Return error code is: %s. exiting.",  zfsdstclone, clone)
            print("Clone %s creation failed. Return error code is: %s \nExiting.") % (zfsdstclone, clone)
            sys.exit(1)

        # Mount new clone filesystem as a [/apps|ifxsrv]_clone
        if args.rotateImg == "app":
            service_action(z2, "application/apps1_mount", "apps1dst", "set_prop", zfsdstclone)
            service_action(z2, "application/apps1_mount", "apps1dst", "enable")

            # Run rsync
            service_action(z2, "application/apps1_mount", "apps1sync", "enable")
            time.sleep(1)
            # time.sleep(100)

            while True:
                service_action(z2, "application/apps1_mount", "apps1syncchk", "enable")
                sync_stat = service_action(z2, "application/apps1_mount", "apps1sync", "get_prop")
                service_action(z2, "application/apps1_mount", "apps1syncchk", "disable")
                if sync_stat == "running":
                    logger.info("Sync to /apps1_clone(%s) is still in progress.", zfsdstclone)
                    time.sleep(60)
                elif sync_stat == "initial":
                    close_con()
                    logger.error("Sync to %s never started, the return code is: %s", zfsdstclone, sync_stat)
                    sys.exit(1)
                elif sync_stat == "completed":
                    service_action(z2, "application/apps1_mount", "apps1syncchk", "disable")
                    service_action(z2, "application/apps1_mount", "apps1sync", "disable")
                    logger.info("Sync to /apps1_clone(%s) completed sucssfuly.", zfsdstclone)
                    break
                else:
                    close_con()
                    print "ERROR: An error occurred while trying to sync %s, with error code: (%s)" % (zfsdstclone, sync_stat)
                    logger.error("An error occurred while trying to sync %s, with error code: (%s)", zfsdstclone, sync_stat)
                    sys.exit(1)

            # Umount /apps1 and /apps1_clone
            service_action(z2, "application/apps1_mount", "apps1dst", "disable")
            service_action(z2, "application/apps1_mount", "apps1src", "disable")
        else:
            # Stop Informix DB / Umount /ifxsrv
            service_action(z2, "application/informix_startup", "ifxsrvr", "disable")
            time.sleep(3)
            service_action(z2, "application/informix_mount", "ifxsrc", "disable")

        # Rename snap, clone orignal apps-time/ifxdb-do-time => apps1-newtime/ifxdb-do-newtime
        rename_snap(zfssrcsnap, zfssrcsnap + "-" + dt.strftime("%s"), zfssrcfs)
        rename_clone(zfssrcclone, zfssrcclone + "-" + dt.strftime("%s"))

        # Rename snap, clone orignal apps-time/ifxdb-do-time => apps1-newtime/ifxdb-do-newtime
        rename_snap(zfsdstsnap, zfssrcsnap, zfssrcfs)
        rename_clone(zfsdstclone, zfssrcclone)

        if args.rotateImg == "app":
            # Mount new clone as [/apps1|/ifxsrv]
            service_action(z2, "application/apps1_mount", "apps1src", "enable")
        else:
            service_action(z2, "application/informix_mount", "ifxsrc", "enable")
            # Update Informix IP/port
            service_action(z2, "application/informix_port", "ifxport", "refresh")
            time.sleep(1)
            service_action(z2, "application/informix_startup", "ifxsrvr", "enable")
        close_con()
        logger.info("Rotation of %s(%s) mount in zone %s completed successfully.", zfsmount, zfssrcclone, matchzone)
        print "(%s)Rotation of %s(%s) mount in zone %s completed successfully." % (zfsmount, dc.upper(), zfssrcclone, matchzone)
    else:
        if args.rotateImg == "app":
            service_action(z2, "application/apps1_mount", "apps1src", "disable")
            service_action(z2, "application/apps1_mount", "apps1src", "enable")
        else:
            # Stop Informix DB.
            service_action(z2, "application/informix_mount", "ifxsrc", "disable")
            # Un-mount /ifxsrv orignal informix mount
            service_action(z2, "application/informix_mount", "ifxsrc", "disable")
            # Mount new clone as /ifxsrv
            service_action(z2, "application/informix_mount", "ifxsrc", "enable")
            # Update Informix IP/port
            service_action(z2, "application/informix_port", "ifxport", "refresh")
            # Start Informix DB (normally disabled as we dont start DB in two places for the same mount).
            # service_action(z2, "application/informix_mount", "ifxsrc", "enable")
        close_con()
        logger.info("Re-mount of %s(%s) mount in zone %s completed successfully.", zfsmount, zfssrcclone, matchzone)
        print "(%s)Re-mount of %s(%s) mount in zone %s completed successfully." % (zfsmount, dc.upper(), zfssrcclone, matchzone)

# ********************** Main calls ********************** #


def verif_snap_availability(dc, host):
    """Verify the ZFS snapshot name already exists.
    accepts: data center, host
    returns: ZFS snapshot / clone name exists.
    """
    logger.info('Validating configuration request.')
    for zfssrcfs in zfssrcfslist:
        snap = verif_snap(zfsdstsnap, zfssrcfs)
        if snap == 200:
            close_con()
            print "Snapshot %s exists in %s. Error code: %s  \nExiting." % (zfsdstsnap, zfssrcfs, snap)
            logger.error("Snapshot %s exists in %s. Error code: %s  exiting.", zfsdstsnap, zfssrcfs, snap)
            sys.exit(snap)
        else:
            logger.info("Snapshot %s in %s is valid. continuing...", zfsdstsnap, zfssrcfs)

    for zfsdstclone in zfsdstclonelist:
        clone = verif_clone(zfsdstsnap, zfsdstclone)
        if clone == 200:
            close_con()
            print "Clone %s exists. Error code: %s \nExiting." % (zfsdstclone)
            logger.error("Clone %s exists. Error code: %s exiting.", zfsdstclone, clone)
            sys.exit(snap)
        else:
            logger.info("Clone %s is valid. continuing...", zfsdstclone)


def clone_fs(dc, host, dst_z, drhost):
    """Create a ZFS snapshot.
    accepts: data center, host, zone name (snap/clone name)
    returns: ZFS snapshot / clone created successful.
    """
    verif_snap_availability(dc, host)

    if dst_z != "z-source":
        for h in [host, drhost]:
            close_con()
            host_connect(h)
            src_z = verify_src_zone(src_zone, h)
            close_con()
        host_connect(host)
        # Create ZFS snap.
        for zfssrcfs in zfssrcfslist:
            logger.info("Cerating snapshot: %s for %s", zfsdstsnap, zfssrcfs)
            snap = create_snap(zfsdstsnap, zfssrcfs)
            if snap == 201:
                logger.info("Snapshot created successfully.")
            else:
                close_con()
                logger.error("Snapshot %s creation failed, with error code: %s. exiting.", zfsdstsnap, snap)
                print("Snapshot %s creation failed, with error code: %s \nExiting.") % (zfsdstsnap, snap)
                sys.exit(snap)

        # Verifying ZFS snap availability.
        logger.info("Verifying snapshot availability for %s.", zfssrcfs)
        snap = verif_snap(zfsdstsnap, zfssrcfs)
        if snap == 200:
            logger.info("Snapshot %s available for %s. continuing...", zfsdstsnap, zfssrcfs)
        else:
            close_con()
            logger.error("Error: Snapshot %s for %s is not available. Return error code is: %s. exiting.", zfsdstsnap, zfssrcfs, snap)
            print("Error: Snapshot %s for %s is not available. Return error code is: %s \nExiting.") % (zfsdstsnap, zfssrcfs, snap)
            sys.exit(snap)

        # Cloning file-systems.
        for zfsdstclone in zfsdstclonelist:
            zfssrcfs = zfssrcfslist[(zfsdstclonelist.index(zfsdstclone))]
            logger.info("CLONING file-systems")
            logger.info("Source: /%s", zfssrcfs)
            logger.info("Destination: %s",  zfsdstclone)
            logger.info("Please wait...")
            clone = create_clone(zfsdstsnap, zfsdstclone, zfssrcfs)
            if clone == 201:
                logger.info("Successfully created clone %s",  zfsdstclone)
            else:
                logger.error("Clone %s creation failed. Return error code is: %s. exiting.",  zfsdstclone, clone)
                close_con()
                print("Clone %s creation failed. Return error code is: %s \nExiting.") % (zfsdstclone, clone)
                sys.exit(1)


def clone_vm(dc, host):
    """Clone zone and file system - source to destination.
    accepts: data center, global zone.
    """
    if dc == "dr":
        set_logging(dst_zone + "(" + dc.upper() + ")")

    print "Cloning VM/Zone %s and associated file systems\nProgress is being logged to %s\n--------------------------------" % (dst_zone, log_output)

    # Checking source zone exists.
    logger.info("Checking source zone exists...")
    if dc == "dr":
        host_connect(host)
    else:
        close_con()
        host_connect(host)
    matchzone = verify_zone_exist("z-source")
    if matchzone is None:
        logger.info("Source zone z-source does not exist on %s in %s.", host, dc.upper())
        logger.info("Intsalling / creating z-source, please wait this can take a while...")
        print ("Source zone z-source does not exist in %s. creating z-source...\nPlease wait... this can take a while..." % dc.upper())
        dst_z = create_dst_zone("z-source")

        # Set zone prop
        prep_zone(dst_z)

        # Create source zone profile
        profile_loc = run_remote_cmd(dst_z.name, 31005, host, "/tmp/", str(get_file_data("conf/" + sc_profile_templ, dc)), "-sc_profile.xml")
        manifest_loc = create_src_zone_manifest(dst_z, host)

        # Install zone
        install_src_zone(dst_z, host, profile_loc, manifest_loc)

        # Boot source zone
        boot_zone(dst_z)

        # Check for zone availability.
        connect_to_zone(dst_z, "confmgr")

        # Create ip and mount services
        create_src_zone_service(dst_z, host)

        # Enable NFS mounts
        enable_src_zone_nfs(dst_z, host)

        # Restart the manifest-import service (to import new smf).
        service_action(dst_z, "system/manifest-import", "default", "restart")

        # Halting zone to make ready for cloning
        time.sleep(2)
        dst_z.halt(None)
    else:
        logger.info("Source zone %s exists, continuing", "z-source")

    # Checking source zone availability.
    logger.info("Checking source zone availability...")
    src_z = verify_src_zone(src_zone, host)

    # Configuring destination zone.
    dst_z = create_dst_zone(dst_zone)
    logger.info("All checks in %s passed, continuing.", dc.upper())
    prep_zone(dst_z)

    # Clone source to destination zone.
    logger.info("CLONING VM/Zone")
    logger.info("Source zone: %s", src_z.name)
    logger.info("Destination zone: %s", dst_z.name)
    logger.info("Please wait...")
    dbPort = clone_zone(src_z, dst_z, host, dc)
    logger.info("Successfully created zone %s", dst_z.name)

    # Boot zone.
    boot_zone(dst_z)

    # ---===== Prep zone =====----
    #
    # Check for zone availability.
    connect_to_zone(dst_z, "confmgr")

    # Create LDAP certficates in zone path.
    if get_config('LDAP', 'ldap') == "yes":
        for cert in cert_list:
            cert_data = get_file_data('conf/' + cert, dc)
            file_loc = run_remote_cmd(dst_z.name, None, host, "/zones/" + dst_z.name + "/root/var/ldap/" + cert, cert_data, ".pem")

    # Restart LDAP service after certficates are copied
    service_action(dst_z, "network/ldap/client", "default", "restart")

    # Enable service to mount /apps1.
    service_action(dst_z, "application/apps1_mount", "apps1src", "enable")

    # Get zone ip address and port
    ipAddr, ipPort = service_action(dst_z, "network/getIpPort", "ip", "get_prop")

    # Enable service to start informix DB.
    if dc == "ha":
        # Start informix DB.
        service_action(dst_z, "application/informix_startup", "ifxsrvr", "enable")

    # Get zone IP adn Port.
    if dc == "ha":
        logger.info("******* Informix Database is only running in %s *******", host)
        print("===============================================================")
        print("******* NOTE: Informix is only running on %s *******") % (host)
        print("                         (%s)                       ") % (host.split("-")[1])
        print("===============================================================")
        logger.info("New VM/Zone is available on %s, with IP Address: %s Port %s DB Port %s", host, ipAddr, ipPort, int(ipPort) + 500)

        print "\n-------========= Active data center =========------- \n        VM/Zone Name: %s \n        Hostname: %s \n        Zone Port: %s \n        DB Port: %s \n        Internal IP Address: %s" % (dst_z.name, host.split("-")[1], ipPort, int(ipPort) + 500, ipAddr)
    else:
        print "\n-------========= Standby data center =========------- \n        VM/Zone Name: %s \n        Hostname: %s \n        Zone Port: %s \n        DB Port: %s \n        Internal IP Address: %s" % (dst_z.name, host, ipPort, int(ipPort) + 500, ipAddr)
        logger.info("New VM/Zone is available on %s, with IP Address: %s Port %s DB Port %s", host, ipAddr, ipPort, int(ipPort) + 500)
    close_con()
    print "        VM Mount source: apps1_%s" % (matchzone)
    print "        DB Mount source: ifxdb-do_%s" % (matchzone)
    print "        VM Mount destination: /apps1"
    print "        DB Mount destination: /ifxsrv"

    # Close connection.
    close_con()

    logger.info("Installation of zone %s in %s successfully completed.", dst_z.name, dc.upper())
    print "Installation of zone %s in %s successfully completed." % (dst_z.name, dc.upper())


def delete_filesystem():

    """Deletes a ZFS file system."""
    logger.info("Deleting clone/snapshots related to zone: %s", matchzone)

    for zfssrcfs in zfssrcfslist:
        for snap in get_snap_list('snap_' + matchzone, zfssrcfs):
            logger.info("Snap %s related to zone %s for %s, will be deleted.", snap, matchzone, zfssrcfs)
            delete_clone = delete_snap(snap, zfssrcfs)
            if delete_clone == 204:
                close_con()
                logger.info("Clone/snapshot for %s and associated snap_%s deleted successfully.", zfssrcfs, snap)
            else:
                close_con()
                print("ERROR: Clone snap_%s for %s deletion failed. Return error code is: %s \nExiting.") % (snap, zfssrcfs, delete_clone)
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
        matchzone = verify_zone_exist("-" + jiraid + "$")
        if matchzone is not None:
            print "Found %s on %s in %s." % (jiraid, host[dc], dc.upper())
            logger.info("Found %s on %s.", jiraid, host[dc])
            break
        else:
            logger.info("No VM/Zone for %s on %s.", jiraid, host[dc])
    if matchzone is None:
        close_con()
        print "ERROR: Cannot find VM/Zone for %s on any of the servers in %s." % (jiraid, dc.upper())
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
    if matchzone != "z-source":
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
            main(dc, host_grp, None)
        sys.exit(0)
    if drstat == "both":
        for dc in dclist:
            if dc == "ha":
                host_grp = dc_host_list(hostdclist, dc)
                drhost_grp = dc_host_list(hostdclist, "dr")
                if args.delete or args.imgStat or args.rotateImg:
                    main(dc, host_grp, None)
                else:
                    print "Evaluating system resources availability. Please wait..."
                    hid, host = gz_to_use(dc, host_grp)
                    main(dc, host_grp[hid-1]['ha'], drhost_grp[hid-1]['dr'])
            else:
                host_grp = dc_host_list(hostdclist, dc)
                hahost_grp = dc_host_list(hostdclist, "ha")
                if args.delete or args.imgStat or args.rotateImg:
                    main(dc, host_grp, None)
                else:
                    main(dc, host_grp[hid-1]['dr'], hahost_grp[hid-1]['ha'])
