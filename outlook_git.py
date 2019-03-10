import os
import requests
import json
import socket
import itertools
from datetime import datetime
from datetime import timedelta


# It will be worth checking out this link on Getting Started with MS Graph O-Auth flow
# https://docs.microsoft.com/en-us/graph/auth-v2-user

######### DEFINE ENV ('prod', 'qa', 'dev') ###############
env = 'dev' 



# Get Client - Id/Secret (of MS App) registered
cred_conf = {}
try:
	cred_confFile = open("cred_conf.json", 'r')
	cred_conf = json.loads(cred_confFile)
except:
	print("Graph Crentials file missing")
	exit(-1)

if( len(cred_conf['client_id']) or len(cred_conf['client_secret']) or len(cred_conf['redirect_uri']) or len(cred_conf['scope'])):
	print("One or more credentials are empty, please correct!")
	exit(-1)

client_id = cred_conf['client_id']
client_secret = cred_conf['client_secret']
redirect_uri = cred_conf['redirect_uri']


# scope = 'user.read+Mail.ReadWrite+Mail.Send'
scope = cred_conf['scope']

######### FOLDER ID MAP UPDATE ###########
folderIdMap = {}
try:
	host_foldermap = open("folderIdMap.json", 'r')
	folderIdMap = json.loads(host_foldermap.read())
except:
	print("Folder ID map not found")

##### InfluxDB COnfig. ########
influxConfig = {}
try:
	inf_conf = open("influxDb_config.json", 'r')
	influxConfig_all = json.loads(inf_conf.read())
	influxConfig = influxConfig_all[env]
except:
	pass


######################
# eventMap = {
# 	'error': {
# 		'threshold': 3,
# 		'timePeriod': 3
# 	}
# }

eventMap = {}
try:
	config_file = open("alert_config.json", 'r')
	eventMap = json.loads(config_file.read())
except:
	print("No Events config file found")
	exit()

################
eventTimeStamps = {}
eventHosts = {}



# Get the below URL
# auth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id="+ client_id +"&redirect_uri=" +  redirect_uri + "&response_type=code&scope=offline_access+" + scope
# https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=c5ce7a56-2a52-45ff-a530-b7183c04e7bb&redirect_uri=http://localhost/&response_type=code&scope=offline_access%20user.read%20mail.readwrite%20mail.send


#enter the Auth code to genereate the Refresh token
# end-point to use

#
def writeNowTime():
	global token_timestamp
	f = open('/tmp/.time_stamp', 'w')
	f.write(str(token_timestamp))
	f.close()


# get refesh token
def get_set_refreshToken():
	global auth_code
	global refresh_token
	token_endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
	headers = {'Content-Type': 'application/x-www-form-urlencoded'}
	p_load = "tenant=common&grant_type=authorization_code&code="+ auth_code + "&redirect_uri=" + redirect_uri + "&client_id=" + client_id + "&client_secret=" + client_secret
	response = requests.post(token_endpoint, data=p_load, headers=headers)
	if response.status_code == 200 and response.text != None:
		parsed_response = json.loads(response.text)
		refresh_token = str(parsed_response['refresh_token'])
		return refresh_token
	else:
		print("Generate Refresh_Access_token - Failed - Exiting")
		exit(-1)

# get access token
def get_accessToken():
	global refresh_token
	global client_id
	global client_secret
	global redirect_uri
	token_endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
	headers = {'Content-Type': 'application/x-www-form-urlencoded'}
	p_load = "tenant=common&grant_type=refresh_token&refresh_token="+ refresh_token + "&redirect_uri=" + redirect_uri + "&client_id=" + client_id + "&client_secret=" + client_secret
	response = requests.post(token_endpoint, data=p_load, headers=headers)
	if response.status_code == 200 and response.text != None:
		parsed_response = json.loads(response.text)
		access_token = str(parsed_response['access_token'])
		return access_token
	else:
		print("Generate Access_token - Failed - Exiting")
		exit(-1)


def access_token():
	global refresh_token
	global token
	global token_timestamp
	if refresh_token == '':
		print("No Refresh Token - Exiting")
		exit(-1)
		#get_set_refreshToken()
	if token == '':
		token = get_accessToken()	
		token_timestamp = datetime.now()
		writeNowTime()
	else:
		try:
			f = open('/tmp/.time_stamp', 'r')
			token_timestamp = datetime.strptime(f.read(), '%Y-%m-%d %H:%M:%S.%f')	
			f.close()	
			nowTime =  datetime.now()
			deltaTime = (nowTime - token_timestamp).seconds
			if deltaTime.seconds > 2700:
				token = get_accessToken()
				token_timestamp = datetime.now()
				writeNowTime()
		except:
			token = get_accessToken()	
			token_timestamp = datetime.now()
			writeNowTime()
	return token


def folderId():
	global folderIdMap
	hostname = socket.gethostname()
	if folderIdMap.get(hostname) != None:
		return folderIdMap[hostname]
	else:
		url = 'https://graph.microsoft.com/v1.0/me/mailFolders'
		headers = {'Authorization': 'Bearer '+access_token() , 'Content-Type': 'application/json'}
		#list all and see if exists:
		response = requests.get(url, headers=headers)
		if response.status_code == 200:
			parsed_response = json.loads(response.text)
			folders = parsed_response['value']
			for item in folders:				
				if str(item['displayName']) == hostname:					
					folderIdMap[hostname] = item['id']
					f = open('folderIdMap.json', 'w')
					f.write(json.dumps(folderIdMap))
					f.close()
					return item['id']
			createURL = 'https://graph.microsoft.com/v1.0/me/mailFolders'
			p_load = {'displayName': hostname}
			head = {'Authorization': 'Bearer '+access_token() , 'Content-Type': 'application/json'}
			response2 = requests.post(createURL, json=p_load, headers=head)
			if response2.status_code == 201:
				parsed_response2 = json.loads(response2.text)
				if str(parsed_response2['displayName']) == hostname:
					folderIdMap[hostname] = parsed_response2['id']
					f = open('folderIdMap.json', 'w')
					f.write(json.dumps(folderIdMap))
					f.close()
					return parsed_response2['id']
				else:
					exit(-1)
			else:
				exit(-1)
		else:
			exit(-1)


def moveEmail(msgId):
	hostname = socket.gethostname()
	url = 'https://graph.microsoft.com/v1.0/me/messages/' + msgId + '/move'
	headers = {'Authorization': 'Bearer '+access_token() , 'Content-Type': 'application/json'}
	p_load = {'destinationId': folderId()}
	response = requests.post(url, json=p_load, headers=headers)
	if response.status_code == 201:
		parsed_response = json.loads(response.text)
		return parsed_response['id']
	return ''

def makeBatch(endpoint, method, ids, payload=[], operation=""):
	batch = {}
	batch['requests'] = []
	count= 1
	for i in ids:
		blck = {'id': count, 'method': method, 'url': endpoint + i + operation}
		batch['requests'].append(blck)


def listUnread(folderId='inbox'):
	msgIds = []
	#url = 'https://graph.microsoft.com/v1.0/me/mailFolders/'+ folderId + '/messages'
	url = 'https://graph.microsoft.com/v1.0/me/mailFolders/'+ folderId + '/messages?$filter=isRead eq false&$select=id&$orderby=createdDateTime'
	headers = {'Authorization': 'Bearer '+access_token() , 'Content-Type': 'application/json', 'outlook.body-content-type': 'text'}
	#p_load = {'destinationId': folderId}
	response = requests.get(url, headers=headers)
	if response.status_code == 200:
		parsed_response = json.loads(response.text)
		messages = parsed_response['value']
		msgIds = []
		for msg in messages:
			msgIds.append(msg['id'])
	else:
		print('Inbox unreachable - Listing failed')
		exit(-1)
	return msgIds


def processEmails(listIds):
	global influxFlag
	global eventMap
	global eventTimeStamps
	headers = {'Authorization': 'Bearer '+access_token() , 'Content-Type': 'application/json', 'outlook.body-content-type': 'text'}
	for msId in listIds:
		url = 'https://graph.microsoft.com/v1.0/me/messages/' + msId
		response = requests.get(url, headers=headers)
		if response.status_code == 200:
			message = json.loads(response.text)
			if influxFlag == 1:
				insertInflux(message)
			alrtMsg = message['subject']
			if alrtMsg in eventMap.keys():
				dtTime = datetime.strptime(message['createdDateTime'], '%Y-%m-%dT%H:%M:%SZ')
				host = message['sender']['emailAddress']['address']
				eventTimeStamps[alrtMsg][host]['Ids'].append(msId)
				eventTimeStamps[alrtMsg][host]['timeStamp'].append(dtTime)
	if influxFlag == 0:
	 	processAlerts()

def processAlerts():
	global eventMap
	global eventTimeStamps
	for k in eventTimeStamps.keys():
		timePeriod = eventMap[k]['timePeriod']
		timeDiff = timedelta(minutes=timePeriod[0], seconds=timePeriod[1])
		threshold =  eventMap[k]['threshold']
		for host in eventTimeStamps[k].keys():
			errorArray	= eventTimeStamps[k][host]['timeStamp']
			if len(errorArray) >= threshold:
				while(len(eventTimeStamps[k][host]['Ids']) >= threshold):
					errorArray = eventTimeStamps[k][host]['timeStamp']
					idsArray = eventTimeStamps[k][host]['Ids']
					deltaArr = [y-x for x, y in itertools.izip(errorArray, errorArray[1:])]
					sumtime = timedelta(minutes=0, seconds=0)
					for i in deltaArr[0:threshold-1]:
						sumtime += i
					if sumtime <= timeDiff:
						genAlert(k, [str(dt) for dt in errorArray[0:threshold]])
						for popi in range(0, threshold):
							markAsRead(eventTimeStamps[k][host]['Ids'][0])
							eventTimeStamps[k][host]['Ids'].pop(0)
							eventTimeStamps[k][host]['timeStamp'].pop(0)
					else:
						markAsRead(eventTimeStamps[k][host]['Ids'][0])
						eventTimeStamps[k][host]['Ids'].pop(0)
						eventTimeStamps[k][host]['timeStamp'].pop(0)
					


def markAsRead(msgId):
	headers = {'Authorization': 'Bearer '+access_token() , 'Content-Type': 'application/json', 'outlook.body-content-type': 'text'}
	url = 'https://graph.microsoft.com/v1.0/me/messages/' + msgId
	body = {'isRead': True}
	response = requests.patch(url, json=body, headers=headers)
	if response.status_code == 200:
		return True

def insertInflux(host, error, timeStamp):
	global influxConfig
	timeStamp = int((timeStamp-datetime(1970, 1, 1)).total_seconds())
	p_load = "pam_email,host=" + host + ",error=" + error + " count=1 " + str(timeStamp)
	url = influxConfig['url'] + "db=" + influxConfig['db'] + "&precision=s"
	if influxConfig['user'] != '':
		url += '&u=' + influxConfig['user'] + "&p=" + influxConfig['pass']
	resp = requests.post(url, p_load)


def genAlert(errorSubject, messageBody):
	# if we want to send an alert to Bosun/Netcool via APIs
	# for now we send email to Netcool/ops center for eg:
	sendEmail(errorSubject, 'ops@yourDomain.com', messageBody)

def sendEmail(subject, to_address, message):
	print("sendEmail")
	headers = {'Authorization': 'Bearer '+access_token() , 'Content-Type': 'application/json', 'outlook.body-content-type': 'text'}
	url = 'https://graph.microsoft.com/v1.0/me/sendMail/'
	body = {
	'message': {
	    "subject": subject,
	    "importance":"High",
	    "body":{
		        "contentType":"Text",
		        "content": str(message)
		    },
		    "toRecipients":[
		        {
		            "emailAddress":{
		                "address": to_address
		            }
		        }
		    ]
		}
	}
	print(body)
	response = requests.post(url, json=body, headers=headers)
	print(response)
	if response.status_code == 202:	
		return True
	



def createeventTimeStamps():
	hosts = ['linux23usa']
	for k in eventMap.keys():
		eventTimeStamps[k] = {}
		for host in hosts:
			eventTimeStamps[k][host] = {}
			eventTimeStamps[k][host]['Ids'] = []
			eventTimeStamps[k][host]['timeStamp'] = []
	return 



### Intiliazating variables and methods

createeventTimeStamps()
influxFlag = 0

########################

# folderId = 'AQMkA......CAQwAAAA='




token = ''

refresh_token = 'MCRpsnCfEOgb......*pvc4oRejbzXjIwsocd*o$'

if (len(refresh_token) == 0):
	# auth_code = input()
	auth_code = 'Mf6............cc4'
	print "Using the auth_code to get the refresh token: " + str(auth_code)
	get_set_refreshToken()

unread_msgs = []
moved_ids = []


unread_msgs = listUnread('inbox')
if len(unread_msgs) == 0:
	unread_msgs = listUnread('inbox')
	for msg in unread_msgs:
		moveEmail(msg)

moved_ids = listUnread(folderId())

processEmails(moved_ids)


















