#!/usr/bin/python
import telnetlib
import re
import os
import serial
import sys
import time
from termcolor import cprint
from random import randint


hidden_start=0
c_wifi_ready=0
r_wifi_ready=0
r_wps_ready=0
trigger_time=0
c2_rssi=telnetlib.Telnet()
r2_rssi=telnetlib.Telnet()
def usage():
    print("Usage: ")
    print("\t %s /dev/ttyUSB0(controller_ip) /dev/ttyUSB1(repeater_ip) ==> 1:console mode 0:telnet mode" % str(sys.argv[0]))
    exit()

def config_com(dut):
    dut.baudrate=115200
    dut.bytesize=serial.EIGHTBITS
    dut.parity=serial.PARITY_NONE
    dut.stopbits=serial.STOPBITS_ONE
    dut.timeout=1
    dut.xonxoff=False
    dut.rtscts=False
    dut.dsrdtr=False
    dut.writeTimeout=2

def device_open(dut, port=" "):
    try:
        dut.open()
    except Exception, e:
        print("Error on open serial %s, error %s" % (port,e))
        exit()

def send_no_read(dut, cmd="\n", dut_str=" "):
    #dut.flushInput()
    #dut.flushOutput()
    dut.write(cmd + "\n")

def flushOutput(dut):
    while True:
        try:
            res = dut.read_until("root@OpenWrt:/#", 1)
            if "OpenWrt" in res:
                #print "Flush out: " + res
                print "Flush output"
            else:
                break
        except Exception,e:
            print "Time out" + str(e)
            break
    return

def sendln(dut, cmd = "\n", dut_str=" ", dbgout=True):
    #dut.flushInput()
    #flushOutput(dut)
    dut.write(cmd + "\n")
    res = dut.read_until("root@OpenWrt:/#")
    if dbgout:
        print dut_str + " Sendln result: " + res
    return res

def reset_controller_default(dut):
    sendln(dut, "uci set wireless.wifi0.hwmode=11ac", "Controller")
    sendln(dut, "uci set wireless.wifi0.htmode=HT80", "Controller")
    sendln(dut, "uci set wireless.wifi0.channel=44", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].ssid=lcs1_tt_wps_5g", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].key=87654321", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].wps_pbc=1", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].encryption=psk2+ccmp", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].key=87654321", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].wps_pbc=1", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].mode=ap", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].wds=1", "Controller")
    sendln(dut, "uci set wireless.wifi0.disabled=0", "Controller")
    sendln(dut, "uci set wireless.@wifi-iface[0].network=wifi0", "Controller")
    sendln(dut, "uci commit", "Controller")
    sendln(dut, "wifi", "Controller")

def reset_repeater_default(dut):
    sendln(dut, "uci set wireless.wifi0.hwmode=11ac", "Repeater")
    sendln(dut, "uci set wireless.wifi0.htmode=HT80", "Repeater")
    sendln(dut, "uci set wireless.wifi0.channel=44", "Repeater")
    sendln(dut, "uci set wireless.@wifi-iface[0].wps_pbc=1", "Repeater")
    sendln(dut, "uci set wireless.@wifi-iface[0].mode=sta", "Repeater")
    sendln(dut, "uci set wireless.@wifi-iface[0].wds=1", "Repeater")
    sendln(dut, "uci set wireless.wifi0.disabled=0", "Repeater")
    sendln(dut, "uci set wireless.@wifi-iface[0].network=wifi0", "Repeater")
    sendln(dut, "uci commit", "Repeater")
    sendln(dut, "wifi", "Repeater" )

def is_wifi_on(dut, retry=5, dut_str=" "):
    print "Checking " + dut_str + " wifi status ...."
    i = 0
    wifi_on=False
    a=0
    while i<retry:
        begin = time.time()
        rc = sendln(dut, "iwconfig ath0", dut_str, False)
        for line in rc.split(" "):
            match = re.findall("Rate:", line)
            if match:
                a = line.split(":")
                break
        rate = 0
        if a:
            i = i + 1 # count retry after wifi on
            rate = int(float(a[1]))
            print dut_str + ":" + " ath0 bit rate: %5f" % float(a[1])
            if rate != 0:
                wifi_on=True
                return wifi_on
        time.sleep(5)
        after = time.time()
        print "loop: "+str(i) +" retry: "+str(retry)+" Time: "+str(after-begin)

    return wifi_on

def wnc_wps_test(controller, repeater):
    status = "FAILED"
    sendln(controller)
    sendln(repeater)
    sendln(controller)
    sendln(repeater)
    sendln(controller)
    sendln(repeater)
    time.sleep(2)
    time.sleep(2)
    cprint("Trigger WPS", 'red', 'on_green')
    global trigger_time
    trigger_time = time.time()
    sendln(controller, 'env -i ACTION=\"pressed\" BUTTON=\"wps\" /sbin/hotplug-call button')
    sendln(repeater, 'env -i ACTION=\"pressed\" BUTTON=\"wps\" /sbin/hotplug-call button')
    wps_success = False
    repeater_wifi = is_wifi_on(repeater, 15, "Repeater")
    if repeater_wifi:
        global r_wps_ready
        r_wps_ready = time.time()
        print "===> WPS Success"
        wps_success = True
    else:
        a = time.time()
        print "!!!! WPS Failed !!!! " + str(a-trigger_time)

    flushOutput(controller)
    flushOutput(repeater)
    if wps_success:
        print "Set hidden on"
        sendln(controller, "iwpriv ath0 hide_ssid 1", "Controller")
        global hidden_start
        hidden_start=time.time()
        c_wifi = False
        r_wifi = False
        global c_wifi_ready
        global r_wifi_ready
        c_wifi_ready = 0
        r_wifi_ready = 0
        retry = 0

        c_wifi = is_wifi_on(controller, 40, "Controller WIFI")
        if not c_wifi:
            print "Controller wifi is not ready"
            status = "FAILED"
            return status
        else:
            c_wifi_ready = time.time()

        r_wifi = is_wifi_on(repeater, 15, "Repeater WIFI")
        if not r_wifi:
            print "Repeater wifi is not ready"
            status = "FAILED"
            return status
        else:
            r_wifi_ready = time.time()

        print "Controller and Repeater WiFi are ready"
        print "Hidden on:Controller wifi ready: " + str(c_wifi_ready - hidden_start)
        print "Hidden on:Repeater wifi ready: " + str(r_wifi_ready - hidden_start)
        status = "OK"
    return status

if __name__ == '__main__':
    total = len(sys.argv)
    if total < 3:
        usage()

    sys.stdout.write("open %s \n" % str(sys.argv[1]))
    sys.stdout.write("open %s \n" % str(sys.argv[2]))
    """
    if sys.argv[3] == 1:
        controller = serial.Serial()
        controller.port=str(sys.argv[1])
        config_com(controller)
        repeater = serial.Serial()
        repeater.port=str(sys.argv[2])
        config_com(repeater)
        device_open(controller, str(sys.argv[1]))
        device_open(repeater, str(sys.argv[2]))
    else:
    """

    i = 1
    ok = 0;
    while i<10041:
        controller = telnetlib.Telnet(str(sys.argv[1]))
        repeater = telnetlib.Telnet(str(sys.argv[2]))
        c2_rssi.open(str(sys.argv[1]))
        r2_rssi.open(str(sys.argv[2]))
        controller.set_debuglevel(0)
        repeater.set_debuglevel(0)
        c2_rssi.set_debuglevel(0)
        r2_rssi.set_debuglevel(0)

        reset_controller_default(controller)
        reset_repeater_default(repeater)
        print "Set hidden off"
        sendln(controller, "iwpriv ath0 hide_ssid 0", "Controller")
        flushOutput(controller)
        flushOutput(repeater)

        c_start_time = time.time()
        controller_wifi = is_wifi_on(controller, 40, "Controller")
        if not controller_wifi:
            print "Controller is not ready"

        c_ready_time = time.time()

        flushOutput(controller)
        flushOutput(repeater)

        rc = "FAILED"
        if controller_wifi:
            rc = wnc_wps_test(controller, repeater)
        if rc == "OK":
            ok = ok + 1
        #print "controller wifi ready time: " + str(c_ready_time - c_start_time)
        print "WPS triggered, repeater WPS ready time: " + str(r_wps_ready-trigger_time)
        #print "After wps success, controller wifi ready time: " + str(c_wifi_ready - hidden_start)
        #print "After wps success, repeater wifi ready time: " + str(r_wifi_ready - hidden_start)
        sys.stdout.write("Test Result: %s \n" % rc)
        print("Test times : %d, OK times: %d" % (i,ok))
        i = i + 1

        sendln(controller, "rm -f /etc/config/wireless")
        sendln(repeater, "rm -f /etc/config/wireless")

	controller.write("reboot && exit\n")
        repeater.write("reboot && exit\n")
        time.sleep(60)

        #a = randint(1,50)
        #print "Add random delay " + str(a)
        #time.sleep(a)

        c2_rssi.close()
        r2_rssi.close()
        controller.close()
        repeater.close()
