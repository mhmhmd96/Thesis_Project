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

update_time = 100
hard = str(update_time+10)
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
	sleep(1)

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
	return cost
	#print cost

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
		# Use a,b,c,d to avoid conflicting with the routing flows
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
def hostThread(client, server, threasnum, priority):
	print(client, server)
	#The path always: dst => src
	paths = {76:'4::7',233: '4::8', 14:'6::9', 235:'6::16', 11:'7::3'}
	
	path = paths[client]
	# h1: source, h2: destination
	h1 = "192.168.122." + str(client)
	h2 = "192.168.122." + str(server)
	pushFlowRules(h1, h2, path, threasnum, str(priority))
	

################################################
# Main
global hostsList
hostsList = {76:201, 233:201, 14:191, 235:191, 11:76}

#global h1,h2

flag = True
priority = 3000
threasnum = 30000

while flag:
	if priority == 65534:
		priority = 3000
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
		
		if threasnum >= 65535:
			threasnum = 30000
		for client, server in hostsList.items():
			#print("i: ", i)
			
			thread = Thread(target = hostThread, args= (client, server, threasnum, priority))
			#thread.start()
			threasnum+=4
			threads.append(thread)
			#thread.join()
		for th in threads:
			print('NEW THREAD')
			th.start()
			sleep(0.2)
	except KeyboardInterrupt:
		break
		exit
	priority+=1
	sleep(update_time)
		
