#!/usr/bin/python
import telnetlib
import re
import os
import serial
import sys
import time
from termcolor import cprint
from random import randint
import datetime


def usage():
    print("Usage: ")
    print("\t %s DUT_IP" % str(sys.argv[0]))
    exit()

def send_no_read(dut, cmd="\n", dut_str=" "):
    dut.write(cmd + "\n")

def flushOutput(dut):
    while True:
        try:
            res = dut.read_until("root@OpenWrt:/#", 1)
            if "OpenWrt" in res:
		flush_out = 1
            else:
                break
        except Exception,e:
            print "Time out" + str(e)
            break
    return

def sendln(dut, cmd = "\n",dbgout=False):
    dut.write(cmd + "\n")
    res = dut.read_until("root@OpenWrt:/#",20)
    if dbgout:
        print "Sendln result: " + res
    return res

def is_pingable(dut_ip_str="192.168.1.1"):
    while True:
        response = os.system("ping -c 1 -W 1 "+dut_ip_str)
        if response == 0:
            print dut_ip_str+" is pingable"
            return;
        else:
            time.sleep(1)

def hbi_read(dut, reg="0x24"):
    rc = sendln(dut, "hbi_test -d 0 -r "+reg+" 2")
    if "RD:" in rc:
        out="HBI Read: "+rc
        cprint(out, "blue", "on_grey")
        return True
    else:
        cprint ("Failed to read HBI", "white", "on_red")
        return False

def hbi_write(dut, reg="0x2dc", val="0x1dc0"):
    rc = sendln(dut, "hbi_test -d 0 -w "+reg+" "+val)
    if "wr:" in rc:
        out = "HBI Write:"+rc
        cprint(out, "green", "on_grey")
        return True
    else:
        cprint("Failed to write HBI", "white", "on_red")
        return False


if __name__ == '__main__':
    total = len(sys.argv)
    if total < 2:
        usage()

    ipaddr = str(sys.argv[1])
    sys.stdout.write("DUT: open %s \n" % ipaddr)

    ttimes = 0
    loop_ok = 0
    while ttimes < 86400:
        is_pingable(ipaddr)
        time.sleep(2)
        dut = telnetlib.Telnet(ipaddr)
        dut.set_debuglevel(0)

        flushOutput(dut)

        test = 0
        ok = 0
        while test < 10:
            test = test + 1
            sendln(dut, "echo 0 > /sys/class/gpio/gpio36/value")
            time.sleep(2)
            sendln(dut, "echo 1 > /sys/class/gpio/gpio36/value")
            time.sleep(2)

            rc = "FAILED"
            stat = hbi_read(dut, "0x24")
            if not stat:
                print "FAILED"
                continue
            stat = hbi_write(dut, "0x2dc", "0x1dc0")
            if not stat:
                print "FAILED"
                continue
            stat = hbi_read(dut, "0x2dc")
            if not stat:
                print "FAILED"
                continue
            stat = hbi_write(dut, "0x2da", "0x1840")
            if not stat:
                print "FAILED"
                continue
            stat = hbi_write(dut, "0x2da", "0x1dc0")
            if not stat:
                print "FAILED"
                continue
            stat = hbi_read(dut, "0xd0")
            if not stat:
                print "FAILED"
                continue
            ok = ok + 1
        print "OK times: "+str(ok)+ " within one reboot"

        ttimes = ttimes + 1

        if ok==10 or ok>10:
            loop_ok = loop_ok + 1

        print "Test times: "+str(ttimes)+" OK times: "+str(loop_ok)
        send_no_read(dut, "reboot && exit")
        i=0
        while i<11:
            i = i + 1
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(5)

        a = randint(1,10)
        print "Add random delay " + str(a)
        time.sleep(a)

        dut.close()
