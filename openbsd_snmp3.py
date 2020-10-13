#!/usr/bin/env python3
#
# Author: Alexander Naumov <alexander_naumov@opensuse.org>
#
# Copyright (c) 2018-2020 Alexander Naumov, Munich, Germany
#       All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys, os, re, argparse
import subprocess as sp
from datetime import timedelta

VERSION = "0.50 (Oct 2020)"

PF = {
        "pfDescr" : "pfIfDescr",
        "pfIndex" : "pfIfIndex"}

BSD = {
        "cpu_load"    :"hrProcessorLoad",

        "proc_name"   :"hrSWRunName",
        "proc_pid"    :"hrSWRunIndex",
        "proc_param"  :"hrSWRunParameters",
        "proc_cur"    :"hrSystemProcesses",
        "proc_max"    :"hrSystemMaxProcesses",
        "proc_state"  :"hrSWRunStatus",
        "proc_type"   :"hrSWRunType",

        "mem_total"   :"hrMemorySize",
        "mem_used"    :"hrStorageUsed",

        "iface_index" :"ifIndex",
        "iface_name"  :"ifName",
        "iface_type"  :"ifType",
        "iface_IN"    :"ifHCInOctets",
        "iface_OUT"   :"ifHCOutOctets",
        "iface_Speed" :"ifSpeed",
        "iface_MTU"   :"ifMtu",
        "iface_state" :"ifAdminStatus",
        "iface_mac"   :"ifPhysAddress",
        "iface_iIndex":"ipAdEntIfIndex",
        "iface_dic"   :"ipAdEntAddr",
        "iface_oErr"  :"ifOutErrors",
        "iface_iErr"  :"ifInErrors",
        "iface_conn"  :"ifConnectorPresent",

        "storage"     :"hrStorageDescr",
        "allocation"  :"hrStorageAllocationUnits",
        "used"        :"hrStorageUsed",
        "size"        :"hrStorageSize",

        "RAID_index"  :"raidIndex",
        "RAID_name"   :"raidName",
        "RAID_status" :"raidStatus",
}


def snmpwalk(s, OID):
	if (OID == "hrSystemUptime"):
		a = sp.run(["snmpwalk", "-Ov",
         "-u", s["sec_name"],
         "-A", s["auth_pass"],
         "-a", s["auth_proto"],
         "-X", s["priv_pass"],
         "-x", s["priv_proto"],
         "-l", s["sec_level"],
         s["hostname"], OID], capture_output=True, text=True).stdout.split("\n")
		return a[0].split(")")[1]

	output = sp.run(["snmpwalk", "-Oq", "-Ov", 
         "-u", s["sec_name"],
         "-A", s["auth_pass"],
         "-a", s["auth_proto"],
         "-X", s["priv_pass"],
         "-x", s["priv_proto"],
         "-l", s["sec_level"],
         s["hostname"], OID], capture_output=True, text=True).stdout.split("\n")

	if OID in ["sysDescr", "hrDeviceDescr", "hrSWRunParameters"]:
		return output

	return [i.split(" ")[0] for i in output]


# FROM rfc2790:
# "The average, over the last minute, of the percentage
# of time that this processor was not idle.
# Implementations may approximate this one minute
# smoothing period if necessary."
def cpu(session):
  try:
    load  = snmpwalk(session, BSD["cpu_load"])[0]
  except:
    print("UNKNOWN: No SNMP answer from " + session.hostname)
    sys.exit(3)

  if load:
    output = "CPU load average %s |'1 min'=%s;" % (load, load)
    return int(load), output
  else:
    print("UNKNOWN: No SNMP answer from " + session.hostname)
    sys.exit(3)


def pf(session):
  for i in snmpwalk(session, PF["pfDescr"]):
    print(i)


def interfaces(session):
  Index, Name, Type, Mtu, State, Mac, OErr, IErr, Conn, Ip, Dic = ([] for i in range(11))

  Index = [i for i in snmpwalk(session, BSD["iface_index"])]
  Name  = [i for i in snmpwalk(session, BSD["iface_name"])]
  Type  = [i for i in snmpwalk(session, BSD["iface_type"])]
  Mtu   = [i for i in snmpwalk(session, BSD["iface_MTU"])]
  State = [i for i in snmpwalk(session, BSD["iface_state"])]
  Mac   = [i for i in snmpwalk(session, BSD["iface_mac"])]
  OErr  = [i for i in snmpwalk(session, BSD["iface_oErr"])]
  IErr  = [i for i in snmpwalk(session, BSD["iface_iErr"])]
  Conn  = [i for i in snmpwalk(session, BSD["iface_conn"])]
  Ip    = [i for i in snmpwalk(session, BSD["iface_iIndex"])]
  Dic   = [i for i in snmpwalk(session, BSD["iface_dic"])]

  Dicto = dict(zip(Ip, Dic))

  print("\nNAME       UP/DOWN    IP                 MAC                  MTU        TYPE                 STATE      I/O ERROR")
  print("===================================================================================================================")
  for i in Index[:-1]:
    try:
      IP = str(Dicto[str(i)])
    except:
      IP = "---------------"
    x = Index.index(i)
    state = "active" if Conn[x] == "true" else "no carrier"

    print("%s %s %s %s %s %s %s %s/%s" % (Name[x].ljust(10), State[x].ljust(10), IP.ljust(18), \
              Mac[x].ljust(20), Mtu[x].ljust(10), Type[x].ljust(20), state.ljust(13), OErr[x], IErr[x]))
  sys.exit(0)

def proc(session):
  LIST_pid, LIST_state, LIST_type, LIST_name, LIST_param = ([] for i in range(5))

  LIST_pid   = [i for i in snmpwalk(session, BSD["proc_pid"])]
  LIST_state = [i for i in snmpwalk(session, BSD["proc_state"])]
  LIST_type  = [i for i in snmpwalk(session, BSD["proc_type"])]
  LIST_name  = [i for i in snmpwalk(session, BSD["proc_name"])]
  LIST_param = [i for i in snmpwalk(session, BSD["proc_param"])]

  print("\nPID        STATE        TYPE            PROC")
  print("================================================================")
  for pid in LIST_pid:
    x = LIST_pid.index(pid)
    print("%s %s %s %s %s" % (pid.ljust(10), LIST_state[x].ljust(12), \
            LIST_type[x].ljust(15), LIST_name[x], LIST_param[x]))
  sys.exit(0)


def process(session, warning, critical):
  proc_max = int(snmpwalk(session, BSD["proc_max"])[0])
  proc_cur = int(snmpwalk(session, BSD["proc_cur"])[0])
  output = "running %s processes [max %s]|processes=%s;%s;%s;0;0" \
          % (proc_cur, proc_max, proc_cur, warning, critical)

  if proc_cur > critical:
    print ("CRITICAL: " + output)
    sys.exit(2)
  elif proc_cur > warning:
    print ("WARNING: " + output)
    sys.exit(1)
  else:
    print ("OK: " + output)
    sys.exit(0)


def os_info(session):
  print ("\nSystem:  " + snmpwalk(session,"sysDescr")[0])
  print ("Uptime: "    + snmpwalk(session,"hrSystemUptime"))
  print ("CPU:     "   + snmpwalk(session,"hrDeviceDescr")[0])
  print ("Contact: "   + snmpwalk(session,"sysContact")[0] + "\n")
  sys.exit(0)


def storage_list(session):
  LIST_fs, LIST_alloc, LIST_size, LIST_used = ([] for i in range(4))

  LIST_fs    = [i for i in snmpwalk(session, BSD["storage"])]
  LIST_alloc = [i for i in snmpwalk(session, BSD["allocation"])]
  LIST_size  = [i for i in snmpwalk(session, BSD["size"])]
  LIST_used  = [i for i in snmpwalk(session, BSD["used"])]

  print ("\n    SIZE\t\tUSED\t\t    AVALIABLE\t\tFILE SYSTEM")
  print ("==================================================================================")

  for p in LIST_fs:
    if (len(p)>0 and p[0] == "/"):
      x = LIST_fs.index(p)
      if (LIST_alloc[x] and LIST_size[x] and LIST_used[x]):
        SIZE = int(LIST_alloc[x]) * int(LIST_size[x])
        USED = int(LIST_alloc[x]) * int(LIST_used[x])
        FREE = SIZE - USED

        PERCENT_FREE  = (int(FREE) / float(SIZE)) * 100
        PERCENT_ALLOC = (int(USED) / float(SIZE)) * 100
        print ("%s\t%s (%.2f %%)\t%s (%.2f %%)" % \
                (sizeof(SIZE).rjust(10), \
                sizeof(USED).rjust(10), \
                PERCENT_ALLOC, \
                sizeof(FREE).rjust(10), \
                PERCENT_FREE) \
                + "\t" + p.ljust(30))
  sys.exit(0)


def sizeof(num, suffix='b'):
  for unit in ['','K','M','G','T','P','E','Z']:
    if abs(num) < 1024.0:
      return "%3.1f %s%s" % (num, unit, suffix)
    num /= 1024.0
  return "%.1f %s%s" % (num, 'Yi', suffix)


def storage(session, fsys):
  LIST_fs, LIST_alloc, LIST_size, LIST_used = ([] for i in range(4))

  LIST_fs = [i for i in snmpwalk(session, BSD["storage"])]

  if len(LIST_fs) == 0:
    print ("UNKNOWN: can't find such information")
    sys.exit(3)

  if fsys in LIST_fs:
    p = LIST_fs.index(fsys)
  else:
    print ("UNKNOWN: can't find such information")
    sys.exit(3)

  LIST_alloc = [i for i in snmpwalk(session, BSD["allocation"])]
  LIST_size  = [i for i in snmpwalk(session, BSD["size"])]
  LIST_used  = [i for i in snmpwalk(session, BSD["used"])]

  SIZE = int(LIST_alloc[p]) * int(LIST_size[p])
  USED = int(LIST_alloc[p]) * int(LIST_used[p])
  FREE = SIZE - USED

  PERCENT_FREE  = (int(FREE) / float(SIZE)) * 100
  PERCENT_ALLOC = (int(USED) / float(SIZE)) * 100

  if fsys in ["Swap space", "Real memory"]:
    return PERCENT_ALLOC, "%s usage: %.2f %% [ %s / %s ]|usage=%.2f;" % \
            (fsys, PERCENT_ALLOC, sizeof(USED), sizeof(SIZE), PERCENT_ALLOC)
  else:
    return PERCENT_ALLOC, "FS usage: %.2f %% [ %s / %s ]|usage=%.2f;" % \
            (PERCENT_ALLOC, sizeof(USED), sizeof(SIZE), PERCENT_ALLOC)


def traffic(session, NIC):
  LIST_name, LIST_In, LIST_Out, LIST_Speed = ([] for i in range(4))

  print(NIC)

  LIST_name = [i for i in snmpwalk(session, BSD["iface_name"])]
  if len(LIST_name) == 0:
    print ("UNKNOWN: can't find such information")
    sys.exit(3)

  if NIC in LIST_name:
    p = LIST_name.index(NIC)
  else:
    print ("UNKNOWN: can't find such information")
    sys.exit(3)

  LIST_In    = [i for i in snmpwalk(session, BSD["iface_IN"])]
  LIST_Out   = [i for i in snmpwalk(session, BSD["iface_OUT"])]
  LIST_Speed = [i for i in snmpwalk(session, BSD["iface_Speed"])]

  NEW_In  = LIST_In[p]
  NEW_Out = LIST_Out[p]
  SPEED   = int(LIST_Speed[p])
  print("SPEED = ", SPEED)

  FILENAME = "/tmp/traffic." + session["hostname"] + "." +NIC
  try:
    IN = open(FILENAME).read()
    OLD_In  = IN.split('\n')[0]
    OLD_Out = IN.split('\n')[1]
  except IOError:
    print ("Could not read cache file. Creating new cache... please try again in 5 mins")

    try:
      with open(FILENAME, 'w') as out:
        out.write(NEW_In + '\n' + NEW_Out)
    except:
      print("Not saved...")
    sys.exit(0)

  #  https://www.cisco.com/c/en/us/support/docs/ip/simple-network-management-protocol-snmp/8141-calculate-bandwidth-snmp.html
  DELTA_In  = ((int(NEW_In)  - int(OLD_In))  * 8 * 100) / 60*5 * SPEED
  DELTA_Out = ((int(NEW_Out) - int(OLD_Out)) * 8 * 100) / 60*5 * SPEED

  print("Interface '%s' - Traffic In: %sbps, Traffic Out: %sbps | 'traffic_in'=%sbps;;;0; 'traffic_out'=%sbps;;;0;" % (NIC, DELTA_In, DELTA_Out, DELTA_In, DELTA_Out))

  try:
    with open(FILENAME, 'w') as out:
      out.write(NEW_In + '\n' + NEW_Out)
  except:
    print("Not saved...")

  sys.exit(0)


def main():
  p = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog = '''

      _____                 ____   _____ _____        _____ _   _ __  __ _____       ____  
     / ___ \               |  _ \ / ____|  __ \      / ____| \ | |  \/  |  __ \     |___ \ 
    / /  / /___  ___  ____ | |_) | (___ | |  | |    | (___ |  \| | \  / | |__) |_   ____) |
   / /  / / __ \/ _ \/ __ \|  _ < \___ \| |  | |     \___ \| . ` | |\/| |  ___/\ \ / /__ < 
  / /__/ / /_/ /  __/ / / /| |_) |____) | |__| |     ____) | |\  | |  | | |     \ V /___) |
  \_____/ .___/\___/_/ /_/ |____/|_____/|_____/     |_____/|_| \_|_|  |_|_|      \_/|____/ 
       /_/
              |    .
          .   |L  /|   .       This script uses SNMPv3 to check memory/swap usage, file system
      _ . |\ _| \--+._/| .      space usage and CPU load average on (remote) OpenBSD system.
     / ||\| Y J  )   / |/| ./    It also shows detailed information about all avaliable file
    J  |)'( |        ` F`.'/     systems, and configured NICs, system information about OS
  -<|  F         __     .-<       and list of running processes.
    | /       .-'. `.  /-. L___       
    J \      <    \  | | O\|.-'                           EXAMPLES:
  _J \  .-    \/ O | | \  |F      
 '-F  -<_.     \   .-'  `-' L__   Checks FS space usage (in %) on '/var' with 'authPriv' secLevel:
__J  _   _.     >-'  )._.   |-'   > ./openbsd_snmp3.py -H <IP_ADDRESS> -u <secName> -A <authPassword>
`-|.'   /_.           \_|   F       -a <authProtocol> -X <privPassword> -x <privProtocol> -l authPriv
  /.-   .                _.<        -O fs:/var -w 80 -c 90
 /'    /.'             .'  `\ 
  /L  /'   |/      _.-'-\       Checks RAM usage (in %) with 'authNoPriv' secLevel:
 /'J       ___.---'\|          > ./openbsd_snmp3.py -u <secName> -A <authPassword> -a <authProtocol>
   |\  .--' V  | `. `            -l authNoPriv -H <IP_ADDRESS> -O mem -w 60 -c 90
   |/`. `-.     `._)              
      / .-.\                 Checks SWAP usage (in %) with 'noAuthNoPriv' secLevel:
      \ (  `\                 > ./openbsd_snmp3.py -u <secName> -l noAuthNoPriv -H <IP_ADDRESS>
       `.\                       -O swap -w 60 -c 90
                                  
''')

  p.add_argument('--version',
          action='version',
          version='%(prog)s \nVersion: '+ str(VERSION))

  p.add_argument('-H',
          required=True,
          dest='host',
          help='IP addess or hostname of the target host')

  p.add_argument('-p',
          dest='port',
          help="UDP port used for the establishing SNMPv3 connection \
                  (default 161)")

  p.add_argument('-t',
          dest='timeout',
          help="Timeout in seconds (default 1)")

  p.add_argument('-r',
          dest='retry',
          help="Number of connection retries (default 3)")

  p.add_argument('-l',
          required=True,
          dest='secLevel',
          help='Set the securityLevel used for SNMPv3 messages (noAuthNoPriv|authNoPriv|authPriv).')

  p.add_argument('-u',
          required=True,
          dest='secName',
          help='Set the securityName used for authenticated SNMPv3 messages.')

  p.add_argument('-a',
          #required=True,
          dest='authProtocol',
          help='Set the authentication protocol (MD5|SHA) used for authenticated SNMPv3 messages.')

  p.add_argument('-A',
          #required=True,
          dest='authPassword',
          help='Set the authentication pass phrase used for authenticated SNMPv3 messages.')

  p.add_argument('-x',
          #required=True,
          dest='privProtocol',
          help='Set the privacy protocol (DES|AES) used for encrypted SNMPv3 messages.')

  p.add_argument('-X',
          #required=True,
          dest='privPassword',
          help='Set the privacy pass phrase used for encrypted SNMPv3 messages.')

  p.add_argument('-O',
          required=True,
          dest='option',
          help='''Target for check. This can be "cpu", "mem", "swap", "fs" \
                  or "proc" - number of running processes. Use \
                  "os" to see operation system information,\
                  "proc" to see table of running processes,\
                  "interfaces" to see statistics about installed \
                  network interfaces and traffic, \
                  "file-systems" to see the statistic of disk \
                  usage on all mounted file systems.''')

  p.add_argument('-w',
          dest='warning',
          help='WARNING threshold')

  p.add_argument('-c',
          dest='critical',
          help='CRITICAL threshold')

  ARG = p.parse_args()

  if ARG.secLevel == "authPriv":
    if ARG.authProtocol is None or \
       ARG.authPassword is None or \
       ARG.privProtocol is None or \
       ARG.privPassword is None:
         p.error("Security Level 'authPriv' requires authProtocol, \
                   authPassword, privProtocol and privPassword.")
         sys.exit(1)

  elif ARG.secLevel == "authNoPriv":
    ARG.privProtocol = u'DEFAULT'
    ARG.privPassword = u'DEFAULT'

    if ARG.authProtocol is None or \
       ARG.authPassword is None:
        p.error("Security Level 'authNoPriv' requires authProtocol and authPassword.")
        sys.exit(1)

  elif ARG.secLevel == "noAuthNoPriv":
    ARG.privProtocol = u'DEFAULT'
    ARG.privPassword = u'DEFAULT'
    ARG.authProtocol = u'DEFAULT'
    ARG.authPassword = u'DEFAULT'

  else:
      p.error("secLevel should be 'authPriv', 'authNoPriv' or 'noAuthNoPriv'")
      sys.exit(1)

  sprint_value = False
  if ARG.option in ["interfaces", "proc"]:
      sprint_value = True

  TOUT = int(ARG.timeout) if ARG.timeout else 1
  PORT = int(ARG.port)    if ARG.port    else 161
  RTRY = int(ARG.retry)   if ARG.retry   else 3

  session = {
		"hostname"   : ARG.host,
		"timeout"    : TOUT,
		"retries"    : RTRY,
		"port"       : PORT,
		"sec_level"  : ARG.secLevel,
		"sec_name"   : ARG.secName,
		"priv_proto" : ARG.privProtocol,
		"priv_pass"  : ARG.privPassword,
		"auth_proto" : ARG.authProtocol,
		"auth_pass"  : ARG.authPassword
	}

  if (ARG.warning is None or ARG.critical is None):
    if   (ARG.option == "file-systems"): storage_list(session)
    elif (ARG.option == "os"):           os_info     (session)
    elif (ARG.option == "proc"):         proc        (session)
    elif (ARG.option == "interfaces"):   interfaces  (session)
    elif (ARG.option[:7] == "traffic" and len(ARG.option)>7):
      traffic(session, ARG.option[8:])
    else: p.parse_args(['-h'])

  else:
    if   (ARG.option == "cpu"):     value, msg = cpu    (session)
    elif (ARG.option == "mem"):     value, msg = storage(session, "Real")
    elif (ARG.option == "swap"):    value, msg = storage(session, "Swap")
    elif (ARG.option == "proc"):    process(session, int(ARG.warning), int(ARG.critical))

    elif (ARG.option[:2] == "fs" and len(ARG.option)>3):
      value, msg = storage(session, ARG.option[3:])

    else: p.parse_args(['-h'])

  if (int(value) >= int(ARG.critical)):
    print("CRITICAL: " + msg + ARG.warning + ";" + ARG.critical + ";0;0")
    sys.exit(2)

  elif (int(value) >= int(ARG.warning)):
    print("WARNING: " + msg + ARG.warning + ";" + ARG.critical + ";0;0")
    sys.exit(1)

  else:
    print("OK: " + msg + ARG.warning + ";" + ARG.critical + ";0;0")
    sys.exit(0)

if __name__ == '__main__':
  main()

