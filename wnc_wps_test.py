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
        i = i + 1
        rc = sendln(dut, "iwconfig ath0", dut_str, False)
        for line in rc.split(" "):
            match = re.findall("Rate:", line)
            if match:
                a = line.split(":")
                break
        rate = 0
        if a:
            rate = int(float(a[1]))
            print dut_str + ":" + " ath0 bit rate: %5f" % float(a[1])
            if rate != 0:
                wifi_on=True
                return wifi_on
            else:
                time.sleep(5)
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
    repeater_wifi = is_wifi_on(repeater, 35, "Repeater")
    if repeater_wifi:
        global r_wps_ready
        r_wps_ready = time.time()
        print "===> WPS Success"
        wps_success = True
    else:
        print "!!!! WPS Failed !!!!"

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
        while True:
            if not c_wifi:
                c_wifi = is_wifi_on(controller, 1, "Controller WIFI")
            elif c_wifi_ready == 0:
                c_wifi_ready = time.time()

            if not r_wifi:
                r_wifi = is_wifi_on(repeater, 1, "Repeater WIFI")
            elif r_wifi_ready == 0:
                r_wifi_ready = time.time()

            if c_wifi and r_wifi:
                print "Controller wifi and Repeater wifi ready"
                wifi_ready = time.time()
                break

        if c_wifi and r_wifi:
            print "Do ping"
            r = sendln(repeater, "ping -c 10 -W 1 192.168.2.1", "controller")
            rc = sendln(controller, "ping -c 10 -W 1 192.168.2.2", "Controller")
            rc = sendln(controller, "echo $?")
            print "Ping result: " + rc
            if "0" in rc:
                print "Ping successfully"
                status = "OK"
                """
                sendln(repeater, "dmesg -c", "repeater", False)
                sendln(controller, "dmesg -c", "controller", False)
                flushOutput(controller)
                flushOutput(repeater)
                send_no_read(repeater, "iperf3 -s>/tmp/server.log&", "Repeater as Server")
                sendln(repeater)
                send_no_read(controller, "iperf3 -c 192.168.2.2 -P 8 -t 20 >/tmp/ctrl_tx.log &", "Controller as TX")
                for i in range(20):
                    sendln(r2_rssi, "iwpriv ath0 txrx_stats 10 && sleep 1 && dmesg -c", "Repeater RSSI")
                send_no_read(controller, "iperf3 -c 192.168.2.2 -P 8 -t 20 -R > /tmp/ctrl_rx.log &", "Controller as RX")
                for i in range(20):
                    sendln(c2_rssi, "iwpriv ath0 txrx_stats 10 && sleep 1 && dmesg -c", "Controller RSSI")
                sendln(controller, "cat /tmp/ctrl_tx.log")
                sendln(controller, "cat /tmp/ctrl_rx.log")
                """
            else:
                status = "FAILED"
                print "Cannot ping repeater"
        #print "Hidden on , WIFI ready time: " + str(wifi_ready-hidden_start)
    return status

def wps_test(controller, repeater):
    status = "FAILED"
    sendln(controller)
    sendln(repeater)
    sendln(controller)
    sendln(repeater)
    sendln(controller)
    sendln(repeater)
    time.sleep(2)
    print("Trigger WPS")
    trigger_time = time.time()
    send_no_read(controller, "dcli sysmgr sys button-press wps 100")
    send_no_read(repeater, "dcli sysmgr sys button-press wps 100")
    wps_success = False
    expired = False
    first_reg = False
    final = False
    start = time.time()
    re_association_time=0
    wps_ok_time=0
    ok_time=0
    first_reg_time = 0
    while True:
        res = controller.readline()
        if res:
            #sys.stdout.write("controller: %s " % res)
            cprint("Controller: " + res, 'red', 'on_green')
        repeater_res = repeater.readline()
        if repeater_res:
            #sys.stdout.write("repeater: %s " % repeater_res)
            cprint("Repeater: " + repeater_res, 'blue', 'on_white')

        if not wps_success and "wps-result" in res:
            if "success" in res:
                print "===>WPS success"
                wps_success=True
                wps_ok_time = time.time()
            else:
                print "!!!! WPS failed"

        if not first_reg and "station-registered" in res:
            print "===> First registration ok"
            first_reg_time = time.time()
            first_reg = True

        if wps_success and first_reg and not expired and "station-expired" in res:
            print "Reassociation"
            expired = True
            re_association_time = time.time()

        if expired and "station-registered" in res:
            cprint("Success to regssiter. DONE", 'green', 'on_red')
            status = "OK"
            ok_time = time.time()
            final = True
            break

        """
        if wps_success and first_reg and not final:
            send_no_read(controller, "iwconfig ath0")
            send_no_read(repeater, "iwconfig ath0")
        """

        now = time.time()
        if (now-start) > 600:
            print " !!!! TIMEOUT " + "WPS: " + str(wps_success) + "first_reg: " + str(first_reg) + ", expired: " + str(expired) + " !!!!"
            break

    print "STATISTICS: wps_success: "+str(wps_ok_time-trigger_time)+" first reg: "+str(first_reg_time-wps_ok_time)+" reassoication start: "+str(re_association_time-wps_ok_time)+" re-registration ok time: "+str(ok_time-re_association_time) 
    print "RAW: trigger time: "+str(trigger_time)+" wps_success: "+str(wps_ok_time)+" first register time: "+str(first_reg_time)+" reassoication time: "+str(re_association_time)+" ok_time: "+str(ok_time)
    sendln(repeater, "p2-factory-reset")
    sendln(controller, "p2-factory-reset")
    time.sleep(2)
    sendln(repeater, "reboot")
    sendln(controller, "reboot")
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
    while i<41:
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
        controller_wifi = is_wifi_on(controller, 35, "Controller")
        if not controller_wifi:
            print "Controller is not ready"
            exit()
        c_ready_time = time.time()

        flushOutput(controller)
        flushOutput(repeater)

        r_wifi_ready=0
        c_wifi_ready=0
        rc = wnc_wps_test(controller, repeater)
        if rc == "OK":
            ok = ok + 1
        print "controller wifi ready time: " + str(c_ready_time - c_start_time)
        print "WPS triggered, repeater WPS ready time: " + str(r_wps_ready-trigger_time)
        print "After wps success, controller wifi ready time: " + str(c_wifi_ready - hidden_start)
        print "After wps success, repeater wifi ready time: " + str(r_wifi_ready - hidden_start)
        sys.stdout.write("Test Result: %s \n" % rc)
        print("Test times : %d, OK times: %d" % (i,ok))
        i = i + 1

        sendln(controller, "rm -f /etc/config/wireless")
        sendln(repeater, "rm -f /etc/config/wireless")

	controller.write("reboot && exit\n")
        repeater.write("reboot && exit\n")
        time.sleep(40)

        a = randint(1,50)
        print "Add random delay " + str(a)
        time.sleep(a)

        controller.close()
        repeater.close()
