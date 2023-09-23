import os
from time import sleep

filename = "heter_client.py"
#os.system("sudo setcap cap_net_raw+ep $(which python3.10)")
while True:
	os.system("python3 "+str(filename))
	sleep(0.5)

