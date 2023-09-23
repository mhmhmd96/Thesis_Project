#!/usr/bin/env python
import requests
from requests.auth import HTTPBasicAuth
import json
import unicodedata
from subprocess import Popen, PIPE
#import time
import networkx as nx
from sys import exit
from threading import Thread
from multiprocessing import Process
from time import sleep
import pickle

SERVER_IP = "192.168.122.178"

global hostsList
hostsList = [163, 135, 171, 17, 70, 170, 188, 251]



update_time = 5
hard = str(update_time+10)
hard_permenant = str(7000)

# Discover the topology and build the grapgh G (using networkx).
def topologyInformation(url):
	global switch
	global deviceMAC
	global deviceIP
	global hostPorts
	global linkPorts
	global G
	global cost
	
	response = requests.get(url, auth=HTTPBasicAuth('admin', 'admin'))
	if(response.ok):
		data = json.loads(response.content)
	else:
		response.raise_for_status()
	for i in data["network-topology"]["topology"]:
		
		if "node" in i:
			for j in i["node"]:
				# Device MAC and IP

				if "host-tracker-service:addresses" in j:
					for k in j["host-tracker-service:addresses"]:
						ip = k["ip"].encode('ascii','ignore')
						mac = k["mac"].encode('ascii','ignore')
						deviceMAC[ip] = mac
						deviceIP[mac] = ip

				# Device Switch Connection and Port

				if "host-tracker-service:attachment-points" in j:

					for k in j["host-tracker-service:attachment-points"]:
						mac = k["corresponding-tp"].encode('ascii','ignore')
						mac = mac.split(b":",1)[1]
						ip = deviceIP[mac].decode('utf-8')
						temp = k["tp-id"].encode('ascii','ignore')
						switchID = temp.split(b":")
						port = switchID[2]
						hostPorts[ip] = port.decode('utf-8')
						switchID = switchID[0].decode('utf-8') + ":" + switchID[1].decode('utf-8')
						switch[ip] = switchID

	# Link Port Mapping
	for i in data["network-topology"]["topology"]:
		if "link" in i:
			for j in i["link"]:
				if "host" not in j['link-id']:
					src = j["link-id"].encode('ascii','ignore').split(b":")
					srcPort = src[2].decode('utf-8')
					dst = j["destination"]["dest-tp"].encode('ascii','ignore').split(b":")
					dstPort = dst[2].decode('utf-8')
					srcToDst = src[1].decode('utf-8') + "::" + dst[1].decode('utf-8')
					linkPorts[srcToDst] = srcPort + "::" + dstPort
					G.add_edge((int)(src[1]),(int)(dst[1]))
					with open("net.pkl", "wb") as file:
                				pickle.dump(G, file)
					
					
# Return information about a link between two nodes
def getStats(url):
	#print ("\nCost Computation....\n")
	response = requests.get(url, auth=HTTPBasicAuth('admin', 'admin'))
	data = json.loads(response.content)
	txRate = 0
	for i in data["node-connector"]:
		tx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["bytes"]["transmitted"])
		rx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["bytes"]["received"])
		txRate = txRate + tx +rx
		#print txRate
	
	# sleep 2 sec
	sleep(2)

	response = requests.get(url, auth=HTTPBasicAuth('admin', 'admin'))
	tempJSON = ""
	if(response.ok):
		tempJSON = json.loads(response.content)
		
	cost =0
	for i in tempJSON["node-connector"]:
		tx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["bytes"]["transmitted"])
		rx = int(i["opendaylight-port-statistics:flow-capable-node-connector-statistics"]["bytes"]["received"])
		cost = cost + tx + rx
	
	cost = cost - txRate
	#print (cost)
	return cost
	

# Send commands from the system.
def systemCommand(cmd):
	terminalProcess = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
	terminalProcess.wait()
	
	#terminalOutput, stderr = terminalProcess.communicate()
	#print ([terminalProcess.returncode, stderr, terminalOutput])
	#if (terminalProcess.returncode or stderr):
		#print ('something went wrong...')
	print ("\n*** Flow Pushed\n")
# Push the flow of the best path in each switch of the flow
def pushFlowRules(h1,h2,bestPath,threasnum,priority):
	
	id= h1+h2
	# We consider the path from h2 to h1
	bestPath = bestPath.split("::")
	
	# Push the flow from (port1 to port2) in each switch in the best path
	for currentNode in range(0, len(bestPath)-1):
		if (currentNode==0):
			inport = hostPorts[h2]
			srcNode = bestPath[currentNode]
			dstNode = bestPath[currentNode+1]
			outport = linkPorts[srcNode + "::" + dstNode]
			outport = outport.split("::")[0]
		else:
			prevNode = bestPath[currentNode-1]
			#print prevNode
			srcNode = bestPath[currentNode]
			#print srcNode
			dstNode = bestPath[currentNode+1]
			inport = linkPorts[prevNode + "::" + srcNode]
			inport = inport.split("::")[1]
			outport = linkPorts[srcNode + "::" + dstNode]
			outport = outport.split("::")[0]

		# Push the binding between ports in the current switch
		flow1=str(threasnum)
		xmlSrcToDst = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'a'+'</flow-name><match><ipv4-destination>'+h1+'/32</ipv4-destination><ipv4-source>'+h2+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>1</cookie><id>'+flow1+'</id><hard-timeout>'+hard+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(outport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''
		
		
		# Push the binding between ports (in the opposite link) in the current switch
		flow2=str(threasnum+1)
		xmlDstToSrc = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'b'+'</flow-name><match><ipv4-destination>'+h2+'/32</ipv4-destination><ipv4-source>'+h1+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>2</cookie><id>'+flow2+'</id><hard-timeout>'+hard+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(inport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''
		
		# Send the flows to the switch
		flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[currentNode] +"/table/0/flow/"+str(flow1)

		command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlSrcToDst

		systemCommand(command)

		flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[currentNode] +"/table/0/flow/"+str(flow2)

		command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlDstToSrc

		systemCommand(command)
		
	# Push the flow from (port1 to port2) in the last switch in the best path (h1)
	print('bestPath', bestPath)
	srcNode = bestPath[-1]
	prevNode = bestPath[-2]
	inport = linkPorts[prevNode + "::" + srcNode]
	inport = inport.split("::")[1]
	outport = hostPorts[h1]
	flow3=str(threasnum+2)

	xmlSrcToDst = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'c'+'</flow-name><match><ipv4-destination>'+h1+'/32</ipv4-destination><ipv4-source>'+h2+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>3</cookie><id>'+flow3+'</id><hard-timeout>'+hard+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(outport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''
	flow4=str(threasnum+3)

	xmlDstToSrc = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'d'+'</flow-name><match><ipv4-destination>'+h2+'/32</ipv4-destination><ipv4-source>'+h1+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>4</cookie><id>'+flow4+'</id><hard-timeout>'+hard+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(inport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''

	flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[-1] +"/table/0/flow/"+str(flow3)

	command = 'curl --user \"admin\":\"admin\" -H \"Accept: application/xml\" -H \"Content-type: application/xml\" -X PUT ' + flowURL + ' -d ' + xmlSrcToDst

	systemCommand(command)

	flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[-1] +"/table/0/flow/"+str(flow4)

	command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlDstToSrc

	systemCommand(command)

###############################
def pushPermenantFlowRules(h1,h2,bestPath,threasnum,priority):
	
	id= h1+h2
	# We consider the path from h2 to h1
	bestPath = bestPath.split("::")
	
	# Push the flow from (port1 to port2) in each switch in the best path
	for currentNode in range(0, len(bestPath)-1):
		if (currentNode==0):
			inport = hostPorts[h2]
			srcNode = bestPath[currentNode]
			dstNode = bestPath[currentNode+1]
			outport = linkPorts[srcNode + "::" + dstNode]
			outport = outport.split("::")[0]
		else:
			prevNode = bestPath[currentNode-1]
			#print prevNode
			srcNode = bestPath[currentNode]
			#print srcNode
			dstNode = bestPath[currentNode+1]
			inport = linkPorts[prevNode + "::" + srcNode]
			inport = inport.split("::")[1]
			outport = linkPorts[srcNode + "::" + dstNode]
			outport = outport.split("::")[0]

		# Push the binding between ports in the current switch
		flow1=str(threasnum)
		xmlSrcToDst = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'a'+'</flow-name><match><ipv4-destination>'+h1+'/32</ipv4-destination><ipv4-source>'+h2+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>1</cookie><id>'+flow1+'</id><hard-timeout>'+hard_permenant+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(outport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''
		
		
		# Push the binding between ports (in the opposite link) in the current switch
		flow2=str(threasnum+1)
		xmlDstToSrc = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'b'+'</flow-name><match><ipv4-destination>'+h2+'/32</ipv4-destination><ipv4-source>'+h1+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>2</cookie><id>'+flow2+'</id><hard-timeout>'+hard_permenant+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(inport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''
		
		# Send the flows to the switch
		flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[currentNode] +"/table/0/flow/"+str(flow1)

		command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlSrcToDst

		systemCommand(command)

		flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[currentNode] +"/table/0/flow/"+str(flow2)

		command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlDstToSrc

		systemCommand(command)
		
	# Push the flow from (port1 to port2) in the last switch in the best path (h1)
	print('bestPath', bestPath)
	srcNode = bestPath[-1]
	prevNode = bestPath[-2]
	inport = linkPorts[prevNode + "::" + srcNode]
	inport = inport.split("::")[1]
	outport = hostPorts[h1]
	flow3=str(threasnum+2)

	xmlSrcToDst = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'c'+'</flow-name><match><ipv4-destination>'+h1+'/32</ipv4-destination><ipv4-source>'+h2+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>3</cookie><id>'+flow3+'</id><hard-timeout>'+hard_permenant+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(outport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''
	flow4=str(threasnum+3)

	xmlDstToSrc = '\'<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?><flow xmlns=\"urn:opendaylight:flow:inventory\"><strict>false</strict><priority>'+priority+'</priority><flow-name>'+id+'d'+'</flow-name><match><ipv4-destination>'+h2+'/32</ipv4-destination><ipv4-source>'+h1+'/32</ipv4-source><ethernet-match><ethernet-type><type>2048</type></ethernet-type></ethernet-match></match><cookie>4</cookie><id>'+flow4+'</id><hard-timeout>'+hard_permenant+'</hard-timeout><table_id>0</table_id><instructions><instruction><order>0</order><apply-actions><action><order>0</order><output-action><output-node-connector>' + str(inport) +'</output-node-connector></output-action></action></apply-actions></instruction></instructions></flow>\''

	flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[-1] +"/table/0/flow/"+str(flow3)

	command = 'curl --user \"admin\":\"admin\" -H \"Accept: application/xml\" -H \"Content-type: application/xml\" -X PUT ' + flowURL + ' -d ' + xmlSrcToDst

	systemCommand(command)

	flowURL = "http://127.0.0.1:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+ bestPath[-1] +"/table/0/flow/"+str(flow4)

	command = 'curl --user "admin":"admin" -H "Accept: application/xml" -H "Content-type: application/xml" -X PUT ' + flowURL + ' -d ' + xmlDstToSrc

	systemCommand(command)

###############################
def hostThread(i,threasnum,priority):
	# h1: source, h2: destination
	h1 = "192.168.122." + str(i)
	h2 = SERVER_IP
	
	paths = [currentPath for currentPath in nx.all_shortest_paths(G, source=int(switch[h2].split(":",1)[1]), target=int(switch[h1].split(":",1)[1]))]
	sorted_list = sorted(paths, key=lambda x:len(x))[0:2]
	unused_paths = sorted(paths, key=lambda x:len(x))[2:]
	for p in unused_paths:
		for node in range(len(p)-1):
			s= p[node]
			d= p[node+1]
			G[s][d]['weight'] = float('inf')*2
			
	# Cost Computation
	paths={}
	pathNum = 1
	for currentPath in sorted_list:
		#Check only the first 3 paths
		if pathNum >3:
			break
		#cost_acc=0
		for node in range(0,len(currentPath)-1):
			#tmp = tmp + str(currentPath[node]) + "::"
			key = str(currentPath[node])+ "::" + str(currentPath[node+1])
			port = linkPorts[key]
			port = port.split(":",1)[0]
			port = int(port)
			
			
			stats = "http://localhost:8181/restconf/operational/opendaylight-inventory:nodes/node/openflow:"+str(currentPath[node])+"/node-connector/openflow:"+str(currentPath[node])+":"+str(port)
			

			#getResponse(stats,"statistics")
			s= currentPath[node]
			d= currentPath[node+1]
			path = str(s) +'-'+ str(d)
			
			cost = getStats(stats)
			paths[path] = cost
			#cost_acc += cost
			G[s][d]['weight'] = cost*2
			pathNum+=1
		#tmp = tmp + str(currentPath[len(currentPath)-1])
		#tmp = tmp.strip("::")
		#finalLinkTX[tmp] = cost_acc


	print ("\nFinal Link Cost\n")
	#print (finalLinkTX)
	pathDijkstra = nx.dijkstra_path(G, source=int(switch[h2].split(":",1)[1]), target=int(switch[h1].split(":",1)[1]), weight='weight')		

	
	# Convert the List path to String
	#The path always: dst => src
	path=''
	for x in pathDijkstra:
		path = path+'::'+str(x)
	#Push Dijkstra Path
	pushFlowRules(h1, h2, path.strip('::'),threasnum,str(priority))
	

################################################
def permenant_flows():
	priority1 = 1000
	threasnum = 65000
	paths = {163:"2::4::7", 70:"2::4::7", 135:"2::4::8", 170:"2::4::8",
		171:"2::6::9", 188:"2::6::9", 17:"2::6::17", 251:"2::6::17"}
	h2 = SERVER_IP
	threads = []
	for i in hostsList:
		h1 = "192.168.122." + str(i)
		#print("i: ", i)
		path = paths[i]
		thread = Thread(target = pushPermenantFlowRules, args= (h1,h2,path,threasnum, str(priority1)))
		#thread.start()
		threasnum+=4
		threads.append(thread)
		#thread.join()
	for th in threads:
		print('Permenant NEW THREAD')
		th.start()
		sleep(0.1)

# Main
counter_permenant = 0
#global h1,h2

flag = True
priority = 10000
threasnum = 1
while flag:
	if priority == 65534:
		priority = 10000
	#Creating Graph
	G = nx.Graph()

	# Stores Info About H3 And H4's Switch
	switch = {}

	# MAC of Hosts i.e. IP:MAC
	deviceMAC = {}

	# IP of Hosts i.e. MAC:IP
	deviceIP = {}

	# Stores Switch Links To H3 and H4's Switch
	switchLinks = {}

	# Stores Host Switch Ports
	hostPorts = {}

	# Stores Switch To Switch Path
	path = {}
	# Stores Link Ports
	linkPorts = {}
	# Stores Final Link Rates
	finalLinkTX = {}
	# Store Port Key For Finding Link Rates
	portKey = ""
	# Statistics
	global stats
	stats = ""
	# Stores Link Cost
	global cost
	cost = 0
	
	try:
 		# Device Info (Switch To Which The Device Is Connected & The MAC Address Of Each Device)
		topology = "http://127.0.0.1:8181/restconf/operational/network-topology:network-topology"
		topologyInformation(topology)

		# Print Device:MAC Info
		print ("\nDevice IP & MAC\n")
		print (deviceMAC)

		# Print Switch:Device Mapping
		print ("\nSwitch:Device Mapping\n")
		print (switch)

		# Print Host:Port Mapping
		print ("\nHost:Port Mapping To Switch\n")
		print (hostPorts)

		# Print Switch:Switch Port:Port Mapping
		print ("\nSwitch:Switch Port:Port Mapping\n")
		print (linkPorts)

		# Paths
		print ("\nAll Paths\n")
		#for path in nx.all_simple_paths(G, source=2, target=1):
			#print(path)
		threads =[]
		if threasnum >= 30000:
			threasnum = 1
		if counter_permenant == 0:
			permenant_flows()
		
		# Increase to avoid pushing permenant flows agian
		counter_permenant+=1
		for i in hostsList:
			#print("i: ", i)
			thread = Thread(target = hostThread, args= (i,threasnum, priority))
			#thread.start()
			threasnum += 4
			threads.append(thread)
			#thread.join()
		for th in threads:
			print('NEW THREAD')
			th.start()
			sleep(0.5)
	except KeyboardInterrupt:
		break
		exit
	priority+=1
	sleep(update_time)
