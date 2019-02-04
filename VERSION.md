<b>Version 0.7.1</b>

<b>Added: </b>Added a service state check loop, since all RAD/SMF service handles are done async, I had to add a check to make sure the service fully stopped before re-started.

<b>Version 0.7</b>
<b>Added / Enhancement: </b>This version greatly improves / simplifies all configuration modifications by using the Python <i>ConfigParser</i> module.
<br>With this version, all configuration details are modified in a new separate configuration file <i>devops_config.ini</i>.
<i>Note: </i>This means the Python <i>ConfigParser</i> module is now a required module.

<b>Updated: </b>The main program <i>clone_zfs.py</i> was re-named to <i>devops_manager.py</i>, for clearance.

<b>Added: </b>With this version you can enable an LDAP supported profile, by enabling LDAP support in the <i>devops_config.ini</i> configuration file.
<i>Note: </i>You can also list/specify a list of certificates to be installed at zone cloning time.

<b>Enhanced: </b>With this version you can enable NFS mount support, by enabling NFS support in the <i>devops_config.ini</i> configuration file.
<br>With this version, you can specify a list of NFS mounts in the <i>devops_config.ini</i> to be configured/mounted at cloning time.

<b>Added: </b>With this version you can add additional services with the <i>devops_config.ini</i> configuration file.
<br>With this version you can also specfy a list of file systems to be cloned.
<i>Note: </i>We are using an external databse with the configuration files stored on a ZFS appliance, being cloned at runtime.

<b>Updated: </b>This version modifies / adds to the <b>-r</b> option, you can now specify <b>-r app</b> or <b>-r db</b>
<br>The <b>-r db</b>, will rotate / create a new ZFS snapshot of the database mount, re-mount the file system, stop/start the DB.
<i>Note: </i>You are not required to use a database mount, this can be enabled/disabled in the <i>devops_config.ini</i> configuration file.

<b>Enhancement: </b>This version catches/fixes a number of application errors, better port allocation/releasing, etc..

<b>Added/Updated: </b>With this version a new structure was created/added a sub directory of <i>bin</i> and of <i>conf</i>
<br>All required files like sc_profile, LDAP certficates, SMF xml files shuld be placed in the <i>conf</i> directory, and all startup scripts shuld be placed in the <i>bin</i> directory.

<b>Version 0.6</b>

<b>Added: </b>This version adds the capability to create Zones with High Availability(HA) and Disaster Recovery(DR) in mind.

<br><img src="images/gz-network-diag-v2.png" alt="Solaris Zone Deployment" align="middle" height="50%"></p>

<br><b>With this version:</b>
<ol>
<li>You can now specify a list of HA (local servers) and a list of DR (remote) servers.</li>
<li>The script will automatically select the least loaded server to create the Zone.</li>
<li>Every zone will get created in pairs, an HA(local) zone and a DR(remote) Zone (based on least load).</li>
<li>The script will also make sure there is enough resources, based on your minimum CPU, Memory, etc...</li>
</ol>

<b>Added: </b>This version adds the VM/Zone image rotate i.e. <b>-l (--listZones)</b> option.
<br>With this version you can now update/rollback an image using the newest ZFS copy.

<b>Added: </b>Add documentation to all Python code functions

<b>Updated: </b>This version enhances / replaces the IP / Port mapping option used in the previous version.
<br>With this version you don't need to create / copy the port mapping file to all zones, the controller(server that runs this script) will keep track of all zone IP / Port mappings. the script utilizes the Python <i>pickleDB</i> module to keep track of this changes, the <i>pickleDB</i> stores all modifications in a JSON like file format called <i>ports.db</i> .

<b>Updated: </b>This version enhances / simplifies and removes the need to create an sc_profile.xml.
<br>With this version there is no need to pre-create the sc_profile.xml, the script will dynamically create the sc_profile.xml at zone install/cloning time.

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
