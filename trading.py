import pymysql
import time
import datetime as dt
import threading
import requests
import json

import jwt
from urllib.parse import urlencode
from collections import OrderedDict

checkTradingEthereum = True


def runTradingEthereum():

	lastCheckNum = 0

	while(checkTradingEthereum == True):
		time.sleep(5)
		tmpCheckNum = _getLastDataNum()
		if(lastCheckNum == tmpCheckNum):
			print("Skip to analyze Price")
			continue
		lastCheckNum = tmpCheckNum

		_getInformation()
		_checkOrderComplite("277")

		ethBalance = _getEthereumBalance()
		print("ethBalance: " + str(ethBalance))

		if(ethBalance > 0.01):
			checkResult = _checkSell()
			if(checkResult == 1):
				_doSellEthereum()
			elif(checkResult == 2):
				print("Pending (Not to Sell Ethereum)")
			else:
				print("_checkSell: Error Code Return")
		elif(ethBalance <= 0.01):
			checkResult = _checkBuy()
			if(checkResult == 1):
				_doBuyEthereum()
			elif(checkResult == 2):
				print("Pending (Not to Buy Ethereum)")
			else:
				print("_checkBuy: Error Code Return")

		analResult = _analPrice(currentStatus)

		if(analResult==1):
			print("Need to Buy")
		elif(analResult==2): 
			print("Need to Sell")
		elif(analResult==3):
			print("Need to Pending")


	return

def _getInformation():

	inputQuery = {'market': 'KRW-ETH'}
	payload = {
		'access_key': '',
		'nonce': int(time.time() * 1000),
		'query': urlencode(inputQuery),
	}
	jwt_token = jwt.encode(payload, '',).decode('utf8')
	authorization = {'Authorization': 'Bearer {}'.format(jwt_token)}

	response = requests.get('https://api.upbit.com/v1/orders/chance', headers=authorization, data=inputQuery)

	print(response.text)
	print("HANETER  END")


	inputQuery = {'market': 'KRW-ETH', 'state': 'wait', 'page': 1, 'order_by': 'asc'}
	payload = {
		'access_key': '',
		'nonce': int(time.time() * 1000),
		'query': urlencode(inputQuery),
	}
	jwt_token = jwt.encode(payload, '',).decode('utf8')
	authorization = {'Authorization': 'Bearer {}'.format(jwt_token)}

	response = requests.get('https://api.upbit.com/v1/orders', headers=authorization, data=inputQuery)

	print(response.text)
	print("HANETER  END")

	return

def _doBuy(volume, price):
	inputQuery = {
		'market': 'KRW-ETH',
		'side': 'bid',
		'volume': str(volume),
		'price': str(price),
		'ord_type': 'limit'
	}

	payload = {
		'access_key': '',
		'nonce': int(time.time() * 1000),
		'query': urlencode(inputQuery),
	}
	jwt_token = jwt.encode(payload, '',).decode('utf8')
	authorization = {'Authorization': 'Bearer {}'.format(jwt_token)}

	response = requests.post('https://api.upbit.com/v1/orders', headers=authorization, data=inputQuery)
	print(response.text)
	return

def _doSell(volume, price):
	inputQuery = {
		'market': 'KRW-ETH',
		'side': 'ask',
		'volume': str(volume),
		'price': str(price),
		'ord_type': 'limit'
	}

	payload = {
		'access_key': '',
		'nonce': int(time.time() * 1000),
		'query': urlencode(inputQuery),
	}
	jwt_token = jwt.encode(payload, '',).decode('utf8')
	authorization = {'Authorization': 'Bearer {}'.format(jwt_token)}

	response = requests.post('https://api.upbit.com/v1/orders', headers=authorization, data=inputQuery)
	print(response.text)
	return

def _checkOrderComplite(uuid):
	print("_checkOrderComplite: " + str(uuid))
	inputQuery = {
		'uuid': str(uuid)
	}
	payload = {
		'access_key': '',
		'nonce': int(time.time() * 1000),
		'query': urlencode(inputQuery),
	}
	jwt_token = jwt.encode(payload, '',).decode('utf8')
	authorization = {'Authorization': 'Bearer {}'.format(jwt_token)}

	response = requests.get('https://api.upbit.com/v1/orders', headers=authorization, data=inputQuery)

	print(response.text)
	print("HANETER  END")
	return

def _getEthereumBalance():
	payload = {
		'access_key': '',
		'nonce': int(time.time() * 1000),
	}
	jwt_token = jwt.encode(payload, '',).decode('utf8')
	authorization = {'Authorization': 'Bearer {}'.format(jwt_token)}

	response = requests.get('https://api.upbit.com/v1/accounts', headers=authorization)

	print(response.text)
	data_list = json.loads(response.text)

	ethBalance = float(0)

	for data in data_list:
		#print("haneter: " + str(data['currency']))
		if(str(data['currency']) == str('ETH')):
			tmpBalance = float(data['balance'])
			tmpLocked = float(data['locked'])
			ethBalance = tmpBalance - tmpLocked

	#print("haneter: " + str(data_list[0]))


	#print("haneter: " + str(data_list[currency]))
	return ethBalance

def _checkSell():

	"""
	Case 1
	매수가격 대비 1% 이상 하락 할 경우
	손절한다.
	"""
	#_getLastBuyData()
	return 0

def _checkBuy():
	currentStatus = _checkCurrentStatus()

	lastDataNum, lastTime, lastUpbitPrice, lastBinancePrice, lastExchangeRate, lastGap, lastGapRate = _getLastPrice()

	lastCandlePrice = _getLastCandlePrice()
	candlePrice_list = json.loads(lastCandlePrice)

	print("HANETER: " + str(candlePrice_list[0]['change_rate_middle_price']))
	for candlePrice in candlePrice_list:
		changeRateMiddlePrice = float(candlePrice['change_rate_middle_price'])
		print("num: " + str(candlePrice['change_rate_middle_price']))

	"""
	Case 1
	50Candle Price > 15 Candle Price > Middle Price 순일 경우
	5연속 하락 후 마지막에 상승 또는 5연속 하락 후 마지막에 하락률 둔하.. (-0.1 이하)
	현재가격에서 1% 상승 가격이 15 Candle Price 보다 작으면
	산다.
	"""
	if float(candlePrice_list[0]['50candle_price']) >= float(candlePrice_list[0]['15candle_price']) and float(candlePrice_list[0]['15candle_price']) >= float(candlePrice_list[0]['middle_price']):
		if float(candlePrice_list['0']['change_rate_middle_price']) > -0.1 and float(candlePrice_list[1]['change_rate_middle_price']) < 0 and float(candlePrice_list[2]['change_rate_middle_price']) < 0 and \
			float(candlePrice_list[3]['change_rate_middle_price']) < 0 and float(candlePrice_list[4]['change_rate_middle_price']) < 0 and float(candlePrice_list[5]['change_rate_middle_price']) < 0:
			if lastUpbitPrice * 1.01 < float(candlePrice_list[0]['15candle_price']):
				print("_checkBuy CASE 1: BUY SIGNAL!!")

	"""
	Case 2
	50 Candle Price > 15 Candle Price > Middle Price 순일 경우
	3연속하락 후 마지막 하락이 둔화 될 때, 한개의 Candle 하락율이 -1 이상인 경우
	마지막 하락이 -0.3 이하로 둔화되었을 경우
	현재 가격에서 1% 상승 가격이 15 Candle Price 보다 작으면
	산다
	"""
	if float(candlePrice_list[0]['50candle_price']) >= float(candlePrice_list[0]['15candle_price']) and float(candlePrice_list[0]['15candle_price']) >= float(candlePrice_list[0]['middle_price']):
		if float(candlePrice_list['0']['change_rate_middle_price']) > -0.3 and float(candlePrice_list[1]['change_rate_middle_price']) < 0 and float(candlePrice_list[2]['change_rate_middle_price']) < 0 and float(candlePrice_list[3]['change_rate_middle_price']) < 0 :
			if float(candlePrice_list[1]['change_rate_middle_price']) < -1  or float(candlePrice_list[2]['change_rate_middle_price']) < -1 or float(candlePrice_list[3]['change_rate_middle_price']) < -1:
				if lastUpbitPrice * 1.01 < float(candlePrice_list[0]['15candle_price']):
					print("_checkBuy CASE 2: BUY SIGNAL!!")
	return 0

def _checkCurrentStatus():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	rowMiddlePrice = []
	rowChangeRateMiddlePrice = []
	count = 0
	checkAbnormal = False

	try:
		cur = dbConn.cursor()
		sql = "select middle_price, change_rate_middle_price from candle_info order by num desc limit 50"
		cur.execute(sql)
		rows = cur.fetchall()

		for row in rows:
			rowMiddlePrice.append(float(row[0]))
			rowChangeRateMiddlePrice.append(float(row[0]))
			if rowChangeRateMiddlePrice[count] >= 1 or rowChangeRateMiddlePrice[count] <= -1:
				checkAbnormal = True
			count = count + 1

		if(checkAbnormal == False):
			if(rowMiddlePrice[0] > rowMiddlePrice[count - 1]):
				returnValue = 1	
			elif(rowMiddlePrice[0] < rowMiddlePrice[count - 1]):
				returnValue = 2
			else:
				returnValue = 3
		elif(checkAbnormal == True):
			if(rowMiddlePrice[0] > rowMiddlePrice[count - 1]):
				returnValue = 4
			elif(rowMiddlePrice[0] < rowMiddlePrice[count - 1]):
				returnValue = 5
			else:
				returnValue = 6

	except:
		print("_checkCurrentStatus Exception!!")
		returnValue = 0
	finally:
		cur.close()
		dbConn.close()
		print("currentStatus is : " + str(returnValue))

	return returnValue

def _getLastDataNum():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select max(num) from data_info_2"
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = int(row[0])
	except:
		rowNum = 0
	finally:
		cur.close()
		dbConn.close()
		print("Last Data Num: " + str(rowNum))
	return rowNum

def _getLastPrice():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select * from data_info_2 order by num desc limit 1"
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = int(row[0])
		rowTime = row[2]
		rowUpbitPrice = float(row[3])
		rowBinancePrice = float(row[4])
		rowExchangeRate = float(row[5])
		rowGap = float(row[6])
		rowGapRate = float(row[7])
	except:
		rowNum = 0
		rowTime = 0
		rowUpbitPrice = 0
		rowBinancePrice = 0
		rowExchangeRate = 0
		rowGap = 0
		rowGapRate = 0
	finally:
		cur.close()
		dbConn.close()
		print("Last Data Price: " + str(rowNum) + ", " + str(rowTime) + ", " +  str(rowUpbitPrice) + ", " + \
			str(rowBinancePrice) + ", " + str(rowExchangeRate) + ", " + str(rowGap) + ", " + str(rowGapRate))

	return rowNum, rowTime, rowUpbitPrice, rowBinancePrice, rowExchangeRate, rowGap, rowGapRate

def _getLastCandlePrice():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select * from candle_info order by num desc limit 10"
		cur.execute(sql)
		rows = cur.fetchall()

		count = 0
		jsonData = "["
		for row in rows:
			if(count != 0):
				jsonData = jsonData + ", "
			tmpJsonData = "{'num':" + str(row[0]) + ", 'data_info_2_num':" + str(row[1]) + ", 'highest_price':'" + str(row[2]) + "', 'lowest_price':'" + str(row[3]) + "', 'start_price':'" + str(row[4]) + \
				"', 'end_price':'" + str(row[5]) + "', '15candle_price':'" + str(row[6]) + "', '50candle_price':'" + str(row[7]) + "', 'middle_price':'" + str(row[8]) + \
				"', 'change_rate_middle_price':'" + str(row[9]) + "', 'change_rate_15candle_price':'" + str(row[10]) + "', 'change_rate_50candle_price':'" + str(row[11]) + "'}"

			jsonData = jsonData + tmpJsonData
			count = count + 1

		jsonData = jsonData + "]"

		print(jsonData)

	except:
		jsonData = ""
	finally:
		cur.close()
		dbConn.close()
		jsonData = jsonData.replace("\'", "\"")

	return jsonData

def _analPrice(currentStatus):
	if(currentStatus == 1):
		print("Normal Up Status")
	elif(currentStatus == 2):
		print("Normal Down Status")
	elif(currentStatus == 3):
		print("Normal Equal Status")
	elif(currentStatus == 4):
		print("Abnormal Up Status")
	elif(currentStatus == 5):
		print("Abnormal Down Status")
	elif(currentStatus == 6):
		print("Abnormal Equal Status")
	elif(currentStatus == 0):
		print("Error Return")
	else:
		print("Unknown Value: " + str(currentStatus))
	return 0

def main():
	global checkTradingEthereum

	checkWhile = True

	while(checkWhile == True):
		print("Trading Program")
		print("1: Start to trade for ethereum")
		print("9: Exit")

		userCmd = input("Please Choose Number: ")

		if(userCmd == '1'):
			print("userCmd is 1")
			th1 = threading.Thread(target = runTradingEthereum)
			th1.start()

		if(userCmd == '9'):
			checkTradingEthereum = False
			checkWhile = False

	print("Exit Program")

if __name__ == "__main__":
	main()
