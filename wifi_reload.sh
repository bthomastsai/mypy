#!/bin/sh

#dmesg -c
ttimes=1
while [ 1 ]; do
    echo 3 > /proc/sys/vm/drop_caches 
    sleep 1 
    cat /proc/meminfo 

	wifi reload
	sleep 3
	hrate=0

	while [ 1 ]; do
            ifconfig ath09 >/dev/null
            if [ "$?" != "0" ]
            then
                echo "Interface no exist"
                exit
            fi
    		if [ "$hrate" == "0" ] 
    		then
			    iwconfig ath09
        		hrate=$(iwconfig ath09 | grep "Bit Rate" | awk '{print $2}' | awk -F':' '{print $2}'| awk -F"." '{print $1}')
			    echo "hrate $hrate"
        		sleep 5
    		else
			    echo "hrate $hrate"
        		break
    		fi
	done
	#dmesg -c
	uptime
	echo "ath09 associate OK, Test times $ttimes"
	ttimes=$(( $ttimes + 1 ))
done
