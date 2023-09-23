import os
from time import sleep

while True:
	os.system('iperf -u -s')
	sleep(0.1)
