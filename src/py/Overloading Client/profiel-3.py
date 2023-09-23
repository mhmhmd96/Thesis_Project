import os
from time import sleep
from subprocess import Popen
import subprocess

data_rate = '60M'
data_rate1 = '60M'
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

		server = '192.168.122.33'
		s1 = Popen('iperf -u -c '+server+' -b '+ data_rate1 +' -t 100', shell=True)
		sleep(0.1)
		server = '192.168.122.191'
		s2 = Popen('iperf -u -c '+server+' -b '+ data_rate1 +' -t 100', shell=True)
		s1.wait()
		s2.wait()
		sleep(0.2)
	sleep(3)
	
	# Round 4
	for i in range(int(time/100)):

		server = '192.168.122.33'
		os.system('iperf -u -c '+server+' -b '+ data_rate +' -t 100')
		sleep(0.2)
	sleep(3)
