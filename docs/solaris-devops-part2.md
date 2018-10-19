This is <a href="solaris-devops-part1.md">Part 2</a>, in <a href="solaris-devops-part1.md">Part 1</a> I described the challenge we try to address as well as the process to configure the network switch, DHCP. Below will continue to configure the source zone as well as all associated SMF services.

<h4>Solaris source zone configuration</h4>
Next, lets create a source zone, you do so by running the below.
<pre>
zonecfg -z z-source <<- 'EOF'
create -t SYSsolaris
set zonepath=/zones/%{zonename}
set autoboot=true
select anet 0
set lower-link=etherstub0
end
EOF
</pre>
Now, lets create an install template, you do so by running the below.
<pre>
cp /usr/share/auto_install/manifest/zone_default.xml z-source.xml
</pre>
Modify the <i>software_data</i> section like the below (add git).
<pre>
      <software_data action="install">
               <name>pkg:/group/system/solaris-small-server</name>
               <name>pkg:/developer/versioning/git</name>
            </software_data>

</pre>
Next, install the source zone by running the below.
<pre>
zoneadm -z z-source install -m z-source_install.xml
</pre>
Now, lets boot the zone.
<pre>
zoneadm -z z-source boot
</pre>
Now, lets get in the console to configure the source zone.
<pre>
zlogin -C z-source
</pre>
Completed the template config by pressing f2, fill with something like the below.
<i>Note: </i> you can also pre-stage a template with sysconfig create-config -o sc_profile.xml, we will be doing so shortly.
<ol>
<li><b>IP Address: </b>10.25.0.2</li>
<li><b>Netmask: </b>255.255.254.0</li>
<li><b>Router: </b>10.25.0.1</li>
<li><b>Or Select:</b> Automatically Since we will be using DHCP anyway</li>
<li><b>DNS: </b>8.8.8.8</li>
<li><b>Domain: </b>example.com</li>
<li><b>Languge: </b>US/Esetren</li>
<li><b>Login/Password: </b>admin/password (or whatever you like)</li>
</ol>
Next, we are going to add a few servicess to help in the zone clone process.
<br>Create the below directory and <i>4</i> files.
<pre>
mkdir -p /opt/cloneFiles
ls
getIpPort.sh  getIpPort.xml  mount_apps1.xml sc_profile.xml
</pre>
Now, lets create the SMF service by creating the below files.
<br>cat mount_apps1.xml
<pre>
<?xml version='1.0'?>
<!DOCTYPE service_bundle SYSTEM '/usr/share/lib/xml/dtd/service_bundle.dtd.1'>
<service_bundle type='manifest' name='export'>
  <service name='application/apps1_mount' type='service' version='0'>
    <create_default_instance enabled='false'/>
    <single_instance/>
    <dependency name='multi-user-server' grouping='require_all' restart_on='none' type='service'>
      <service_fmri value='svc:/milestone/multi-user-server:default'/>
    </dependency>
    <dependency name='dns-client' grouping='require_all' restart_on='none' type='service'>
      <service_fmri value='svc:/network/dns/client:default'/>
    </dependency>
    <dependency name='network' grouping='require_all' restart_on='error' type='service'>
      <service_fmri value='svc:/milestone/network'/>
    </dependency>
    <exec_method name='start' type='method' exec="mount dc1nas2a-web:/export/apps1_`hostname` /apps1" timeout_seconds='10'>
    </exec_method>
    <exec_method name='stop' type='method' exec='umount -f /apps1' timeout_seconds='0'>
    </exec_method>
    <property_group name='startd' type='framework'>
      <propval name='duration' type='astring' value='transient'/>
    </property_group>
    <stability value='Stable'/>
    <template>
      <common_name>
        <loctext xml:lang='C'>Mount /apps1</loctext>
      </common_name>
    </template>
  </service>
</service_bundle>
</pre>
Next, create the application below. this will populate your IP address and port for latter retrieval.
<br><i>Note: </i>The file below contains your IP to Port mappings that is latter used in the clone script.
cat getIpPort.sh
<pre>
#!/bin/bash

ipPortTable="
10.25.0.2:31002
10.25.0.3:31003
10.25.0.4:31004
10.25.0.5:31005
10.25.0.6:31006
10.25.0.7:31007
10.25.0.8:31008
10.25.0.9:31009
10.25.0.10:31010
10.25.0.11:31011
10.25.0.12:31012
10.25.0.13:31013
10.25.0.14:31014
10.25.0.15:31015
10.25.0.16:31016
10.25.0.17:31017
10.25.0.18:31018
10.25.0.19:31019
10.25.0.20:31020
10.25.0.21:31021
10.25.0.22:31022
10.25.0.23:31023
10.25.0.24:31024
10.25.0.25:31025
10.25.0.26:31026
10.25.0.27:31027
10.25.0.28:31028
10.25.0.29:31029
10.25.0.30:31030
10.25.0.31:31031
10.25.0.32:31032
10.25.0.33:31033
10.25.0.34:31034
10.25.0.35:31035
10.25.0.36:31036
10.25.0.37:31037
10.25.0.38:31038
10.25.0.39:31039
10.25.0.40:31040
10.25.0.41:31041
10.25.0.42:31042
10.25.0.43:31043
10.25.0.44:31044
10.25.0.45:31045
10.25.0.46:31046
10.25.0.47:31047
10.25.0.48:31048
10.25.0.49:31049
10.25.0.50:31050
10.25.0.51:31051
10.25.0.52:31052
10.25.0.53:31053
10.25.0.54:31054
10.25.0.55:31055
10.25.0.56:31056
10.25.0.57:31057
10.25.0.58:31058
10.25.0.59:31059
10.25.0.60:31060
10.25.0.61:31061
10.25.0.62:31062
10.25.0.63:31063
10.25.0.64:31064
10.25.0.65:31065
10.25.0.66:31066
10.25.0.67:31067
10.25.0.68:31068
10.25.0.69:31069
10.25.0.70:31070
10.25.0.71:31071
10.25.0.72:31072
10.25.0.73:31073
10.25.0.74:31074
10.25.0.75:31075
10.25.0.76:31076
10.25.0.77:31077
10.25.0.78:31078
10.25.0.79:31079
10.25.0.80:31080
10.25.0.81:31081
10.25.0.82:31082
10.25.0.83:31083
10.25.0.84:31084
10.25.0.85:31085
10.25.0.86:31086
10.25.0.87:31087
10.25.0.88:31088
10.25.0.89:31089
10.25.0.90:31090
10.25.0.91:31091
10.25.0.92:31092
10.25.0.93:31093
10.25.0.94:31094
10.25.0.95:31095
10.25.0.96:31096
10.25.0.97:31097
10.25.0.98:31098
10.25.0.99:31099
10.25.0.100:31100
10.25.0.101:31101
10.25.0.102:31102
10.25.0.103:31103
10.25.0.104:31104
10.25.0.105:31105
10.25.0.106:31106
10.25.0.107:31107
10.25.0.108:31108
10.25.0.109:31109
10.25.0.110:31110
10.25.0.111:31111
10.25.0.112:31112
10.25.0.113:31113
10.25.0.114:31114
10.25.0.115:31115
10.25.0.116:31116
10.25.0.117:31117
10.25.0.118:31118
10.25.0.119:31119
10.25.0.120:31120
10.25.0.121:31121
10.25.0.122:31122
10.25.0.123:31123
10.25.0.124:31124
10.25.0.125:31125
10.25.0.126:31126
10.25.0.127:31127
10.25.0.128:31128
10.25.0.129:31129
10.25.0.130:31130
10.25.0.131:31131
10.25.0.132:31132
10.25.0.133:31133
10.25.0.134:31134
10.25.0.135:31135
10.25.0.136:31136
10.25.0.137:31137
10.25.0.138:31138
10.25.0.139:31139
10.25.0.140:31140
10.25.0.141:31141
10.25.0.142:31142
10.25.0.143:31143
10.25.0.144:31144
10.25.0.145:31145
10.25.0.146:31146
10.25.0.147:31147
10.25.0.148:31148
10.25.0.149:31149
10.25.0.150:31150
10.25.0.151:31151
10.25.0.152:31152
10.25.0.153:31153
10.25.0.154:31154
10.25.0.155:31155
10.25.0.156:31156
10.25.0.157:31157
10.25.0.158:31158
10.25.0.159:31159
10.25.0.160:31160
10.25.0.161:31161
10.25.0.162:31162
10.25.0.163:31163
10.25.0.164:31164
10.25.0.165:31165
10.25.0.166:31166
10.25.0.167:31167
10.25.0.168:31168
10.25.0.169:31169
10.25.0.170:31170
10.25.0.171:31171
10.25.0.172:31172
10.25.0.173:31173
10.25.0.174:31174
10.25.0.175:31175
10.25.0.176:31176
10.25.0.177:31177
10.25.0.178:31178
10.25.0.179:31179
10.25.0.180:31180
10.25.0.181:31181
10.25.0.182:31182
10.25.0.183:31183
10.25.0.184:31184
10.25.0.185:31185
10.25.0.186:31186
10.25.0.187:31187
10.25.0.188:31188
10.25.0.189:31189
10.25.0.190:31190
10.25.0.191:31191
10.25.0.192:31192
10.25.0.193:31193
10.25.0.194:31194
10.25.0.195:31195
10.25.0.196:31196
10.25.0.197:31197
10.25.0.198:31198
10.25.0.199:31199
10.25.0.200:31200
10.25.0.201:31201
10.25.0.202:31202
10.25.0.203:31203
10.25.0.204:31204
10.25.0.205:31205
10.25.0.206:31206
10.25.0.207:31207
10.25.0.208:31208
10.25.0.209:31209
10.25.0.210:31210
10.25.0.211:31211
10.25.0.212:31212
10.25.0.213:31213
10.25.0.214:31214
10.25.0.215:31215
10.25.0.216:31216
10.25.0.217:31217
10.25.0.218:31218
10.25.0.219:31219
10.25.0.220:31220
10.25.0.221:31221
10.25.0.222:31222
10.25.0.223:31223
10.25.0.224:31224
10.25.0.225:31225
10.25.0.226:31226
10.25.0.227:31227
10.25.0.228:31228
10.25.0.229:31229
10.25.0.230:31230
10.25.0.231:31231
10.25.0.232:31232
10.25.0.233:31233
10.25.0.234:31234
10.25.0.235:31235
10.25.0.236:31236
10.25.0.237:31237
10.25.0.238:31238
10.25.0.239:31239
10.25.0.240:31240
10.25.0.241:31241
10.25.0.242:31242
10.25.0.243:31243
10.25.0.244:31244
10.25.0.245:31245
10.25.0.246:31246
10.25.0.247:31247
10.25.0.248:31248
10.25.0.249:31249
10.25.0.250:31250
10.25.0.251:31251
10.25.0.252:31252
10.25.0.253:31253
10.25.0.254:31254
10.25.0.255:31255
10.25.1.1:32001
10.25.1.2:32002
10.25.1.3:32003
10.25.1.4:32004
10.25.1.5:32005
10.25.1.6:32006
10.25.1.7:32007
10.25.1.8:32008
10.25.1.9:32009
10.25.1.10:32010
10.25.1.11:32011
10.25.1.12:32012
10.25.1.13:32013
10.25.1.14:32014
10.25.1.15:32015
10.25.1.16:32016
10.25.1.17:32017
10.25.1.18:32018
10.25.1.19:32019
10.25.1.20:32020
10.25.1.21:32021
10.25.1.22:32022
10.25.1.23:32023
10.25.1.24:32024
10.25.1.25:32025
10.25.1.26:32026
10.25.1.27:32027
10.25.1.28:32028
10.25.1.29:32029
10.25.1.30:32030
10.25.1.31:32031
10.25.1.32:32032
10.25.1.33:32033
10.25.1.34:32034
10.25.1.35:32035
10.25.1.36:32036
10.25.1.37:32037
10.25.1.38:32038
10.25.1.39:32039
10.25.1.40:32040
10.25.1.41:32041
10.25.1.42:32042
10.25.1.43:32043
10.25.1.44:32044
10.25.1.45:32045
10.25.1.46:32046
10.25.1.47:32047
10.25.1.48:32048
10.25.1.49:32049
10.25.1.50:32050
10.25.1.51:32051
10.25.1.52:32052
10.25.1.53:32053
10.25.1.54:32054
10.25.1.55:32055
10.25.1.56:32056
10.25.1.57:32057
10.25.1.58:32058
10.25.1.59:32059
10.25.1.60:32060
10.25.1.61:32061
10.25.1.62:32062
10.25.1.63:32063
10.25.1.64:32064
10.25.1.65:32065
10.25.1.66:32066
10.25.1.67:32067
10.25.1.68:32068
10.25.1.69:32069
10.25.1.70:32070
10.25.1.71:32071
10.25.1.72:32072
10.25.1.73:32073
10.25.1.74:32074
10.25.1.75:32075
10.25.1.76:32076
10.25.1.77:32077
10.25.1.78:32078
10.25.1.79:32079
10.25.1.80:32080
10.25.1.81:32081
10.25.1.82:32082
10.25.1.83:32083
10.25.1.84:32084
10.25.1.85:32085
10.25.1.86:32086
10.25.1.87:32087
10.25.1.88:32088
10.25.1.89:32089
10.25.1.90:32090
10.25.1.91:32091
10.25.1.92:32092
10.25.1.93:32093
10.25.1.94:32094
10.25.1.95:32095
10.25.1.96:32096
10.25.1.97:32097
10.25.1.98:32098
10.25.1.99:32099
10.25.1.100:32100
10.25.1.101:32101
10.25.1.102:32102
10.25.1.103:32103
10.25.1.104:32104
10.25.1.105:32105
10.25.1.106:32106
10.25.1.107:32107
10.25.1.108:32108
10.25.1.109:32109
10.25.1.110:32110
10.25.1.111:32111
10.25.1.112:32112
10.25.1.113:32113
10.25.1.114:32114
10.25.1.115:32115
10.25.1.116:32116
10.25.1.117:32117
10.25.1.118:32118
10.25.1.119:32119
10.25.1.120:32120
10.25.1.121:32121
10.25.1.122:32122
10.25.1.123:32123
10.25.1.124:32124
10.25.1.125:32125
10.25.1.126:32126
10.25.1.127:32127
10.25.1.128:32128
10.25.1.129:32129
10.25.1.130:32130
10.25.1.131:32131
10.25.1.132:32132
10.25.1.133:32133
10.25.1.134:32134
10.25.1.135:32135
10.25.1.136:32136
10.25.1.137:32137
10.25.1.138:32138
10.25.1.139:32139
10.25.1.140:32140
10.25.1.141:32141
10.25.1.142:32142
10.25.1.143:32143
10.25.1.144:32144
10.25.1.145:32145
10.25.1.146:32146
10.25.1.147:32147
10.25.1.148:32148
10.25.1.149:32149
10.25.1.150:32150
10.25.1.151:32151
10.25.1.152:32152
10.25.1.153:32153
10.25.1.154:32154
10.25.1.155:32155
10.25.1.156:32156
10.25.1.157:32157
10.25.1.158:32158
10.25.1.159:32159
10.25.1.160:32160
10.25.1.161:32161
10.25.1.162:32162
10.25.1.163:32163
10.25.1.164:32164
10.25.1.165:32165
10.25.1.166:32166
10.25.1.167:32167
10.25.1.168:32168
10.25.1.169:32169
10.25.1.170:32170
10.25.1.171:32171
10.25.1.172:32172
10.25.1.173:32173
10.25.1.174:32174
10.25.1.175:32175
10.25.1.176:32176
10.25.1.177:32177
10.25.1.178:32178
10.25.1.179:32179
10.25.1.180:32180
10.25.1.181:32181
10.25.1.182:32182
10.25.1.183:32183
10.25.1.184:32184
10.25.1.185:32185
10.25.1.186:32186
10.25.1.187:32187
10.25.1.188:32188
10.25.1.189:32189
10.25.1.190:32190
10.25.1.191:32191
10.25.1.192:32192
10.25.1.193:32193
10.25.1.194:32194
10.25.1.195:32195
10.25.1.196:32196
10.25.1.197:32197
10.25.1.198:32198
10.25.1.199:32199
10.25.1.200:32200
10.25.1.201:32201
10.25.1.202:32202
10.25.1.203:32203
10.25.1.204:32204
10.25.1.205:32205
10.25.1.206:32206
10.25.1.207:32207
10.25.1.208:32208
10.25.1.209:32209
10.25.1.210:32210
10.25.1.211:32211
10.25.1.212:32212
10.25.1.213:32213
10.25.1.214:32214
10.25.1.215:32215
10.25.1.216:32216
10.25.1.217:32217
10.25.1.218:32218
10.25.1.219:32219
10.25.1.220:32220
10.25.1.221:32221
10.25.1.222:32222
10.25.1.223:32223
10.25.1.224:32224
10.25.1.225:32225
10.25.1.226:32226
10.25.1.227:32227
10.25.1.228:32228
10.25.1.229:32229
10.25.1.230:32230
10.25.1.231:32231
10.25.1.232:32232
10.25.1.233:32233
10.25.1.234:32234
10.25.1.235:32235
10.25.1.236:32236
10.25.1.237:32237
10.25.1.238:32238
10.25.1.239:32239
10.25.1.240:32240
10.25.1.241:32241
10.25.1.242:32242
10.25.1.243:32243
10.25.1.244:32244
10.25.1.245:32245
10.25.1.246:32246
10.25.1.247:32247
10.25.1.248:32248
10.25.1.249:32249
10.25.1.250:32250
10.25.1.251:32251
10.25.1.252:32252
10.25.1.253:32253
10.25.1.254:32254
10.25.1.255:32255
"

myIp=`ipadm show-addr -p -o addr net0/v4| awk -F\/ '{print $1}'`
ipPort=`echo "$ipPortTable"|grep ^$myIp:`

addr=`echo $ipPort |awk -F\: '{print $1}'`
port=`echo $ipPort |awk -F\: '{print $2}'`

svccfg -s svc:/network/getIpPort:ip setprop config/ip_addr = astring: $addr
svccfg -s svc:/network/getIpPort:ip setprop config/ip_port = astring: $port
</pre>
Make the application excutable
<pre>
chmod +x getIpPort.sh
</pre>
Create the getIpPort SMF xml file.
<br>cat getIpPort.xml
<pre>
<?xml version='1.0'?>
<!DOCTYPE service_bundle SYSTEM '/usr/share/lib/xml/dtd/service_bundle.dtd.1'>
<service_bundle type='manifest' name='export'>
  <service name='network/getIpPort' type='service' version='0'>
   <single_instance/>
    <dependency name='network' grouping='require_all' restart_on='error' type='service'>
      <service_fmri value='svc:/milestone/network'/>
    </dependency>
   <exec_method name='stop' type='method' exec=':true' timeout_seconds='60'/>
   <property_group name='startd' type='framework'>
      <propval name='duration' type='astring' value='transient'/>
   </property_group>
   <instance name='ip' enabled='true' complete='true'>
    <exec_method name='start' type='method' exec='/opt/cloneFiles/getIpPort.sh' timeout_seconds='5'/>
    <exec_method name='stop' type='method' exec='/opt/cloneFiles/getIpPort.sh' timeout_seconds='5'/>
    <exec_method name='refresh' type='method' exec='/opt/cloneFiles/getIpPort.sh' timeout_seconds='5'/>
      <property_group name='config' type='application'>
        <propval name='ip_addr' type='astring' value=''/>
        <propval name='ip_port' type='astring' value=''/>
      </property_group>
   </instance>
   <stability value='Stable'/>
   <template>
      <common_name>
        <loctext xml:lang='C'>Get IP Address and Port</loctext>
      </common_name>
   </template>
  </service>
</service_bundle>
</pre>
Create the SMF services by importing.
<pre>
# Import SMF service
svccfg import getIpPort.xml
svccfg import mount_apps1.xml

# Verify the new services
svcs mount_apps1 getIpPort
root@z-source:~# svcs apps1_mount getIpPort
STATE          STIME    FMRI
disabled       12:24:32 svc:/application/apps1_mount:default
online         12:24:35 svc:/network/getIpPort:ip
</pre>
Switch the zone to use DHCP before creating / running the sysconfig to create the profile, this will be used in all clones, do so by running the below.
<pre>
ipadm create-addr -T dhcp net0/v4
</pre>
Next, create source template on the Global Zone, this template will be used for all zones when the script will do the cloning.
<pre>
sysconfig create-profile -o /opt/sc_profile.xml
</pre>
For the template use something like the below configuration.
<ol>
<li><b>Or Select:</b> Automatically Since we will be using DHCP in all clones</li>
<li><b>DNS: </b>8.8.8.8</li>
<li><b>Domain: </b>example.com</li>
<li><b>Language: </b>US/Eastern</li>
<li><b>Login/Password: </b>admin/password (or whatever you like)</li>
</ol>
An exmaple is below <i>/opt/sc_profile.xml</i> file (or use sysconfig to generate  one).
<pre>
<?xml version='1.0' encoding='US-ASCII'?>
<!DOCTYPE service_bundle SYSTEM "/usr/share/lib/xml/dtd/service_bundle.dtd.1">
<!-- Auto-generated by sysconfig -->
<service_bundle type="profile" name="sysconfig">
  <service version="1" type="service" name="system/identity">
    <instance enabled="true" name="node">
      <property_group type="application" name="config">
        <propval type="astring" name="nodename" value="z1"/>
      </property_group>
    </instance>
  </service>
  <service version="1" type="service" name="network/physical">
    <instance enabled="true" name="default">
      <property_group type="application" name="netcfg">
        <propval type="astring" name="active_ncp" value="Automatic"/>
      </property_group>
    </instance>
  </service>
  <service version="1" type="service" name="system/name-service/switch">
    <property_group type="application" name="config">
      <propval type="astring" name="default" value="files"/>
    </property_group>
    <instance enabled="true" name="default"/>
  </service>
  <service version="1" type="service" name="system/name-service/cache">
    <instance enabled="true" name="default"/>
  </service>
  <service version="1" type="service" name="system/environment">
    <instance enabled="true" name="init">
      <property_group type="application" name="environment">
        <propval type="astring" name="LANG" value="en_US.UTF-8"/>
      </property_group>
    </instance>
  </service>
  <service version="1" type="service" name="system/timezone">
    <instance enabled="true" name="default">
      <property_group type="application" name="timezone">
        <propval type="astring" name="localtime" value="US/Eastern"/>
      </property_group>
    </instance>
  </service>
  <service version="1" type="service" name="system/config-user">
    <instance enabled="true" name="default">
      <property_group type="application" name="root_account">
        <propval type="astring" name="type" value="role"/>
        <propval type="astring" name="login" value="root"/>
        <propval type="astring" name="password" value="$5$jn8eXfiz$zqxHwPxBc0UHD2e0z34zMndm7G5ghtFBGoSklg7F8N4"/>
      </property_group>
      <property_group type="application" name="user_account">
        <propval type="astring" name="roles" value="root"/>
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
</service_bundle>
</pre>

Make sure to shutdown the <i>z-source</i> zone, otherwise the clone process wont work.
<pre>
zoneadm -z z-source halt
</pre>
We are almost ready for the fun part.
Lets verify if the RAD deamon is enabled.
<pre>
svcs -a |grep rad
...
online         17:45:37 svc:/system/rad:local
online         17:45:37 svc:/system/rad:local-http
online         17:45:37 svc:/system/rad:remote
</pre>
Also make sure you have the RAD modules installed, do so by running the below.
<br><i>Note: </i>In 11.4 you shuld have twice the amount from below.
<pre>
pkg list |grep rad
group/system/management/rad/rad-server-interfaces 0.5.11-0.175.3.29.0.4.0    i--
system/management/rad                             0.5.11-0.175.3.34.0.2.0    i--
system/management/rad/client/rad-c                0.5.11-0.175.3.32.0.1.0    i--
system/management/rad/client/rad-java             0.5.11-0.175.3.32.0.1.0    i--
system/management/rad/client/rad-python           0.5.11-0.175.3.29.0.4.0    i--
system/management/rad/module/rad-dlmgr            0.5.11-0.175.3.29.0.4.0    i--
system/management/rad/module/rad-files            0.5.11-0.175.3.29.0.4.0    i--
system/management/rad/module/rad-kstat            0.5.11-0.175.3.29.0.4.0    i--
system/management/rad/module/rad-network          0.5.11-0.175.3.32.0.1.0    i--
system/management/rad/module/rad-panels           0.5.11-0.175.3.29.0.4.0    i--
system/management/rad/module/rad-smf              0.5.11-0.175.3.29.0.4.0    i--
system/management/rad/module/rad-time             0.5.11-0.175.3.29.0.4.0    i--
system/management/rad/module/rad-usermgr          0.5.11-0.175.3.32.0.1.0    i--
system/management/rad/module/rad-zfsmgr           0.5.11-0.175.3.32.0.1.0    i--
system/management/rad/module/rad-zonemgr          0.5.11-0.175.3.32.0.1.0    i--
</pre>
Finally, we can now use the script to clone zones, the usage options are below.
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
<i>Note: </i>Before using the script, make sure to updated the settings like user/password ZFSSA IP address, etc. that reflects your environment.

Some of the script settings.
<pre>
# ====================== ZFS related ======================

# Add proxy
#os.environ['http_proxy'] = "http://10.10.10.10:1234/"
#os.environ['https_proxy'] = "http://10.10.10.10:1234/"

# ZFSSA API URL
url = "https://10.250.109.110:215"

# ZFSSA API login 
zfsuser = ('user')
zfspass = ('password')
zfsauth = (zfsuser,zfspass)

# ZFS pool
zfspool = "HP-pool1"

# ZFS project
zfsproject = "zfs_project"

# ZFS source filesystem
zfssrcfs = "apps1-file-system"

zfsdstsnap = 'snap_' + dst_zone
zfsdstclone = 'apps1_' + dst_zone

# Global zone
hostGz = 'solaris-global-name'

# Source zone
src_zone = "z-source"

</pre>
Cloning a zone.
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
