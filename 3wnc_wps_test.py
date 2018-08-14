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
                #print "Flush output"
		flush_out = 1
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
    res = dut.read_until("root@OpenWrt:/#", 100)
    if dbgout:
        print dut_str + " Sendln result: " + res
    return res

def reset_controller_default(dut):
    sendln(dut, "cp -f /root/AP-wireless /etc/config/wireless", "Controller")
    sendln(dut, "sync;sync;sync", "Controller")
    time.sleep(1)
    sendln(dut, "wifi load", "Controller")

def reset_repeater_default(dut):
    sendln(dut, "cp -f /root/STA-wireless /etc/config/wireless", "Repeater")
    sendln(dut, "sync;sync;sync", "Repeater")
    sendln(dut)
    flushOutput(dut)
    time.sleep(1)
    rc = sendln(dut, "wifi load", "Repeater")
    print "Reset Repeater" + rc
    if "ath09" in rc and "OK" in rc:
	return True
    else:
	return False

def is_wifi_on(dut, retry=5, inf="ath0" ,dut_str=" "):
    print "Checking " + dut_str + " wifi status ...."
    i = 0
    wifi_on=False
    a=0
    while i<retry:
        begin = time.time()
        rc = sendln(dut, "iwconfig "+inf, dut_str, True)
        for line in rc.split(" "):
            match = re.findall("Rate:", line)
            if match:
                a = line.split(":")
                break
        rate = 0
        if a:
            i = i + 1 # count retry after wifi on
            rate = int(float(a[1]))
            print dut_str + ":" + " %s bit rate: %5f" % (inf, float(a[1]))
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
    sendln(controller, 'hostapd_cli -p /var/run/hostapd-wifi0 -i ath08 wps_pbc')
    sendln(repeater, 'wpa_cli -p /var/run/wpa_supplicant-ath09 -i ath09 wps_pbc')
    sendln(controller)
    sendln(repeater)
    flushOutput(controller)
    flushOutput(repeater)
    wps_success = False
    repeater_wifi = is_wifi_on(repeater, 15, "ath09", "Repeater")
    if repeater_wifi:
        global r_wps_ready
        r_wps_ready = time.time()
        print "===> WPS Success"
        wps_success = True
    else:
        a = time.time()
        print "!!!! WPS Failed !!!! " + str(a-trigger_time)
        #exit()

    flushOutput(controller)
    flushOutput(repeater)
    if wps_success:
        print "Set hidden on"
        sendln(controller, "iwpriv ath08 hide_ssid 1", "Controller")
        k=0
        while k<3:
            k=k+1
            rc = sendln(controller, "iwpriv ath08 get_hide_ssid", "Controller")
            if "get_hide_ssid:1" in rc:
                print "SSID is hidden"
                break
            else:
                print "SSID can not be hidden"
                time.sleep(1)
        if k==3:
            status="FAILED"
            return status

        global hidden_start
        hidden_start=time.time()
        c_wifi = False
        r_wifi = False
        global c_wifi_ready
        global r_wifi_ready
        c_wifi_ready = 0
        r_wifi_ready = 0
        retry = 0

        c_wifi = is_wifi_on(controller, 40, "ath08", "Controller WIFI")
        if not c_wifi:
            print "Controller wifi is not ready"
            status = "FAILED"
            return status
        else:
            c_wifi_ready = time.time()

        r_wifi = is_wifi_on(repeater, 15, "ath09", "Repeater WIFI")
        if not r_wifi:
            print "Repeater wifi is not ready"
            status = "FAILED"
            return status
        else:
            r_wifi_ready = time.time()

        print "WPS triggered, repeater WPS ready time: " + str(r_wps_ready-trigger_time)
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
    controller = telnetlib.Telnet(str(sys.argv[1]))
    reset_controller_default(controller)
    controller.close()

    ttimes = 1
    ok = 0;
    while ttimes<86400:
        # Start sniffer
        repeater = telnetlib.Telnet(str(sys.argv[2]))
        controller = telnetlib.Telnet(str(sys.argv[1]))
        sniffer = telnetlib.Telnet("192.168.10.1")
        controller.set_debuglevel(0)
        repeater.set_debuglevel(0)
        sniffer.set_debuglevel(0)

	start_time = time.time()
        tfile = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        sendln(sniffer, "tcpdump -i ath0 -s 0 -w /tmp/usb/sniffer/0GB/"+tfile+"_Test_"+str(ttimes)+".pcap -K -n &", "Sniffer")
        sys.stdout.write("Reset STA config\n")
        sys.stdout.flush()
	reset = False
        reset = reset_repeater_default(repeater)
        if not reset:
		print "Wifi reload failed"
		ttimes = ttimes + 1
		continue

        rwifi = is_wifi_on(repeater, 1, "ath09", "Repeater")

        print "Set hidden off"
        sendln(controller, "iwpriv ath08 hide_ssid 0", "Controller")
        flushOutput(controller)
        flushOutput(repeater)
        i=0
        while i<3:
            i = i+1
            rc = sendln(controller, "iwpriv ath08 get_hide_ssid", "Controller")
            if "get_hide_ssid:0" in rc:
                print "Set hidden SSID = 0 OK"
                break
            else:
                print "Set hidden SSID = 0 failed"
                time.sleep(1)
        if i==3:
            continue

        c_start_time = time.time()
        controller_wifi = is_wifi_on(controller, 40, "ath08", "Controller")
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
        sys.stdout.write("Test Result: %s \n" % rc)
        print("Test times : %d, OK times: %d" % (ttimes,ok))
	end_time = time.time()
        print "=====> Cost time: "+str(end_time - start_time)

        #Sync Sniffer packet
        sendln(sniffer,"killall tcpdump", "Sniffer", False)
        sendln(sniffer, " ", " ", False)
        sendln(sniffer, " ", " ", False)
        sendln(sniffer,"sync;sync;sync", "Sniffer", False)
        #sendln(sniffer, "cp /tmp/Test"+str(i)+".pcap /tmp/usb/sniffer/gs2020e/")
        #sendln(sniffer, "rm -f /tmp/Test"+str(i)+".pcap")
        ttimes = ttimes + 1

        #if rc == "FAILED":
        #   exit()

        #sendln(controller, "rm -f /etc/config/wireless")
        #sendln(repeater, "rm -f /etc/config/wireless")

	#controller.write("reboot && exit\n")
        #repeater.write("reboot && exit\n")
        #time.sleep(60)
        a = randint(1,5)
        print "Add random delay " + str(a)
        time.sleep(a)
        repeater.close()
        controller.close()
        sniffer.close()
