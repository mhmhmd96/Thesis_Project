import os

ports = [8,9,10,16,17,18,19]
limit = 100
for i in ports:
	#cmd = "sudo tc qdisc add dev enp0s"+str(i)+" root tbf rate "+str(limit)+"mbit burst 300kbit latency 1ms"
	cmd = "sudo tc qdisc add dev enp0s"+str(i)+" root netem rate "+str(limit)+"mbit"
	os.system(cmd)
	
print("Links with "+str(limit), " Mbps")
