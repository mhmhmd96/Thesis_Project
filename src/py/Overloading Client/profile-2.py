import os
from time import sleep
from subprocess import Popen
import subprocess

data_rate = '40M'
data_rate1 = '40M'
time = 500
time1 = str(time)

while True:

	# Round 1
	for i in range(int(time/100)):
		server = '192.168.122.33'
		os.system('iperf -u -c '+server+' -b '+ data_rate +' -t 100')
		sleep(0.2)
	sleep(3)
	
	# Round 2	
	for i in range(int(time/100)):

		server = '192.168.122.33'
		os.system('iperf -u -c '+server+' -b '+ data_rate +' -t 100')
		sleep(0.2)
	sleep(3)
	
	# Round 3
	for i in range(int(time/100)):

		server = '192.168.122.191'
		os.system('iperf -u -c '+server+' -b '+ data_rate +' -t 100')
		sleep(0.2)
	sleep(3)
	
	# Round 4
	for i in range(int(time/100)):

		server = '192.168.122.33'
		os.system('iperf -u -c '+server+' -b '+ data_rate +' -t 100')
		sleep(0.2)
	sleep(3)
