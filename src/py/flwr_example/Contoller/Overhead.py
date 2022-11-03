import pyshark
import socket
from threading import Thread
import queue
import os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('192.168.122.107', 6665))
q = queue.Queue(maxsize=2)
flag = ''
round_number = 0


def start1():
	while True:
		data = s.recv(2048).decode()
		data = data.split('::')
		try:
			flag = data[0]
			round_number = data[1]
		except:
			break
		q.queue.clear()
		q.put(data[0])
		q.put(data[1])
		print(flag, round_number)
		if (flag=='False'):
			s.close()
			print('terminate connection..')
			break
def start2():
	i = 0
	flag='True'
	for packet in capture.sniff_continuously():
		i+=int(packet.length)
		if not q.empty():
			flag = q.get()
			round_number = q.get()
			if flag=='False':
				capture.close()
				break
	#for packet in capture:
		#i += int(packet.length)
		#if i%1e6==0:
			#print('Numbre of packets: '+str(len(capture._packets)))
	os.system('sudo capinfos /tmp/load.pcapng')

capture = pyshark.LiveCapture(interface='enp0s3', bpf_filter='tcp port 6633', output_file='/tmp/load.pcapng')
th1 = Thread(target = start1, args=())
th2 = Thread(target = start2, args=())
th1.start()
th2.start()
