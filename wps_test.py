#!/usr/bin/python

import serial
import sys
import time
from termcolor import cprint
from random import randint

def usage():
    print("Usage: ")
    print("\t %s /dev/ttyUSB0(controller) /dev/ttyUSB1(repeater)" % str(sys.argv[0]))
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

def send_no_read(dut, cmd="\n"):
    dut.flushInput()
    dut.flushOutput()
    dut.write(cmd + "\n")

def sendln(dut, cmd = "\n", dut_str=" "):
    dut.flushInput()
    dut.flushOutput()
    dut.write(cmd + "\n")
    while True:
        res = dut.readline()
        sys.stdout.write("%s read: %s" % (dut_str,res))
        if "#" in res:
            break
    return

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
    controller = serial.Serial()
    controller.port=str(sys.argv[1])
    config_com(controller)
    repeater = serial.Serial()
    repeater.port=str(sys.argv[2])
    config_com(repeater)
    device_open(controller, str(sys.argv[1]))
    device_open(repeater, str(sys.argv[2]))

    i = 1
    ok = 0;
    while i<41:
        rc = wps_test(controller, repeater)
        if rc == "OK":
            ok = ok + 1
        sys.stdout.write("Test Result: %s \n" % rc)
        print("Test times : %d, OK times: %d" % (i,ok))
        i = i + 1
        controller_ok = False
        repeater_ok = False
        while not controller_ok or not repeater_ok:
            sys.stdout.write(".")
            sys.stdout.flush()
            if not controller_ok:
                res = controller.readline()
            if not repeater_ok:
                repeater_res = repeater.readline()

            if not controller_ok and "interface wan connected" in res:
                print("Controller boot up")
                controller_ok = True
            if not repeater_ok and "interface lan connected" in repeater_res:
                print("Repeater boot up")
                repeater_ok = True

        a = randint(1,100)
        print "Add random delay " + str(a)
        time.sleep(a)

    controller.close()
    repeater.close()
