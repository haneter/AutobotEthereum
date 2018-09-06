import requests
import json
import threading
import datetime as dt
import time
import pymysql
import queue
from binance.client import Client

checkUpbitThreading = True
checkBinanceThreading = True
checkRecordDataThreading = True
checkCheckStatusThreading = True
checkTradingThreading = True
checkTestThreading = True
checkMakeCandleThreading = True
checkInsertData = 0
globalQueue = queue.Queue()
globalUsdPrice = 0

""" 
0: 아무것도 안 산 상태
1: 사고 있는 중...
2: 샀다...
3: 파는 중...
"""
checkTradingStatus = 0
"""
1: 사야함
2: 팔아야함
"""
sigTradingEthereum = 0
semaphore = threading.Semaphore(1)
gapRateCnt = 0

lastRowNum = 0

def runUsdPrice():
	global globalUsdPrice

	while(1):
		globalUsdPrice = _getExchangeRateData()
		time.sleep(3600)

	return

def runUpbitData():
	global checkUpbitThreading
	global gapRateCnt
	global checkTradingStatus
	global globalUsdPrice
	global sigTradingEthereum

	gapRateCnt = 0
	checkUpbitThreading = True
	print("runUpbitData")

	while(checkUpbitThreading == True):
		time.sleep(10)
		if globalUsdPrice == 0:
			continue

		startTime = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		upbitPrice = _getUpbitData()
		if(upbitPrice == ""):
			print("Cannot get a price from Upbit")
			continue


		binancePrice = _getBinanceData()
		if(binancePrice == ""):
			print("Cannot get a price from Binance")
			continue

		usdtPrice = _getUSDTFromCoinmarketcapData()
		if(usdtPrice == ""):
			print("Cannot get a price from Coinmarketcap")
			continue

		#usdPrice = _getExchangeRateData()
		currentTime = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		print("Get Data Time GAP: " + str(startTime) + " ~ " + str(currentTime))

		_insertDataQueue("KRW-ETH", currentTime, float(upbitPrice), float(binancePrice), float(usdtPrice), float(globalUsdPrice))
		if(checkUpbitThreading == False):
			break

	print("stop runUpbitData")

def runRecordData():
	global checkUpbitThreading
	global checkRecordDataThreading
	global checkInsertData

	checkRecordDataThreading = True

	while(checkRecordDataThreading == True):
		time.sleep(5)
		_insertData()
		if(checkRecordDataThreading == False):
			break

		if(checkInsertData >= 50):
			print("ERROR Stop to Record Data!!")
			checkRecordDataThreading = False
			checkUpbitThreading = False
			break
	return

def runMakeCandle():
	global checkMakeCandleThreading

	checkMakeCandleThreading = True

	while(checkMakeCandleThreading == True):
		time.sleep(10)
		currentTime = dt.datetime.now().strftime('%M')
		print("minute: " + currentTime)
		if(int(currentTime) == 0 or int(currentTime) == 30):
			print("MAKE CANDLE!!")
			lastDataInfoNum = _getLastDatainfoNum()
			lastCandleDataNum = _getLastCandleDataNum()
			#if(lastDataInfoNum == 0 or lastCandleDataNum == 0):  #데이터 못가지고오면 작업을 하지 않는다.
			#	continue

			if(lastDataInfoNum > lastCandleDataNum + 10): #10은 대강 값을 잡은것... 별 의미 없음
				highestPrice = _getHighestPrice()
				lowestPrice = _getLowestPrice()
				startPrice = _getStartPrice()
				endPrice = _getEndPrice()
				middlePrice = float((startPrice + endPrice) / 2)
				candle15Price = _get15CandlePrice(middlePrice)
				candle50Price = _get50CandlePrice(middlePrice)

				changeRateOfMiddlePrice = _getChangeRateOfMiddlePrice(lastCandleDataNum, middlePrice)
				changeRateOf15Candle = _getChangeRateOf15Candle(lastCandleDataNum, candle15Price)
				changeRateOf50Candle = _getChangeRateOf50Candle(lastCandleDataNum, candle50Price)

				_setCandlePrice(lastDataInfoNum, highestPrice, lowestPrice, startPrice, endPrice, candle15Price, candle50Price, middlePrice, changeRateOfMiddlePrice, changeRateOf15Candle, changeRateOf50Candle)

		if checkMakeCandleThreading == False:
			print("Stop to Make Candle")
			break

	return

def runCheckStatus():
	global checkCheckStatusThreading
	checkCheckStatusThreading = True

	while(checkCheckStatusThreading == True):
		time.sleep(10)
		if(_checkLastRowNum() == False):
			continue
		if(_getGapRateStatus() == False):
			continue
		#_getUpbitPriceAngle()
		#_getBinancePriceAngle()
		if(checkCheckStatusThreading == False):
			break

	return

def runTradingEtherem():
	global gapRateCnt
	global checkTradingThreading
	global sigTradingEthereum

	checkTradingThreading = True

	while(checkTradingThreading == True):
		time.sleep(5)

		if(sigTradingEthereum == 1):
			_buyEthereum()
			gapRateCnt = 0
			sigTradingEthereum = 0

		if(sigTradingEthereum == 2):
			_sellEthereum()
			sigTradingEthereum = 0

		if(checkTradingThreading == False):
			break

	return

def _getSellSignal():
	"""
	시나리오는 체크 순서임.
	"""

	"""
	Scenario 1
	매수한 가격 대비 1% 하락하였을 경우
	손절 매도 한다.
	"""
	"""
	Scenario 2
	"Buy Scenario 1" 을 통해 구매했을 경우,
	현재가격이 15 Candle Price에 도달하면 
	매도한다.
	"""
	"""
	Scenario 3
	"Buy Scenario 2" 을 통해 구매했을 경우,
	현재가격이 50 Candle Price에 도달하면 
	매도한다.
	"""

	"""
	Scenario 4
	50 Candle Price 가 가장 작고, 15 Candle Price가 그다음, Middle Price가 가장 높을 때...
	((15 Candle Price - 50 Candle Price) * 2) + 15 Candle Price 값보다 현재 가격이 높고,
	Middle Price의 가격 상승이 연속 5개 일 때는
	매도한다.
	"""

	"""
	Scenario 5
	매수한 가격 대비 1% 상승하였을 경우
	이익 매도 한다.
	"""

	return 1

def _getBuySignal():

	"""
	Buy Scenario 1
	50 Candle Price 가 가장 크고, 15 Candle Price가 그 다음, Middle Price가 가장 작을 때...
	(15 Candle Price - (50 Candle Price - 15 Candle Price) * 2) 값보다 현재가격이 낮고,
	Middle Price의 가격 하락이 연속 5개 일 때는
	매수 한다.
	"""

	"""
	Buy Scenario 2
	15 Candle Price 가 가장 크고, 50 Candle Price가 그 다음, Middle Price가 가장 작을 때...
	(50 Candle Price - (15 Candle Price - 50 Candle Price) * 2) 값보다 현재가격이 낮고,
	Middle Price의 가격 하락이 연속 5개 일 때는
	매수 한다.
	"""
	return 1

def _getLastDatainfoNum():
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
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = int(row[0])
	except:
		rowNum = 0
	finally:
		cur.close()
		dbConn.close()
		print("ROWNUM: " + str(rowNum))
	return rowNum

def _getLastCandleDataNum():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select max(data_info_2_num) from candle_info"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = int(row[0])
	except:
		rowNum = 0
	finally:
		cur.close()
		dbConn.close()
		print("CANDLE INFO: " + str(rowNum))
	return rowNum

def _getHighestPrice():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select upbit_price from data_info_2 where record_time between date_sub(now(), interval 30 minute) and now() order by upbit_price desc"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = float(row[0])
	except:
		rowNum = 0
	finally:
		cur.close()
		dbConn.close()
		print("HIGHEST PRICE: " + str(rowNum))
	return rowNum

def _getLowestPrice():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select upbit_price from data_info_2 where record_time between date_sub(now(), interval 30 minute) and now() order by upbit_price asc"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = float(row[0])
	except:
		rowNum = 0
	finally:
		cur.close()
		dbConn.close()
		print("LOWEST PRICE: " + str(rowNum))
	return rowNum

def _getStartPrice():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select upbit_price from data_info_2 where record_time between date_sub(now(), interval 30 minute) and now() order by num asc"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = float(row[0])
	except:
		rowNum = 0
	finally:
		cur.close()
		dbConn.close()
		print("START PRICE: " + str(rowNum))
	return rowNum

def _getEndPrice():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select upbit_price from data_info_2 where record_time between date_sub(now(), interval 30 minute) and now() order by num desc"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = float(row[0])
	except:
		rowNum = 0
	finally:
		cur.close()
		dbConn.close()
		print("END PRICE: " + str(rowNum))
	return rowNum

def _get15CandlePrice(middlePrice):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select start_price, end_price from candle_info order by num desc limit 14"
		#print(sql)
		cur.execute(sql)
		rows = cur.fetchall()
		middleTotalPrice = float(0)
		count = 0
		for row in rows:
			startPrice = float(row[0])
			endPrice = float(row[1])
			middleTotalPrice = middleTotalPrice + ((startPrice + endPrice) / 2)
			count = count + 1

		middleTotalPrice = middleTotalPrice + middlePrice
		print("RESULT: " + str(middleTotalPrice) + ", " + str(middlePrice) + ", " + str(count))
		candle15Price = float(middleTotalPrice / (count + 1))
	except:
		candle15Price = 0
	finally:
		cur.close()
		dbConn.close()
		print("15 CANDLE PRICE: " + str(candle15Price))
	return candle15Price

def _get50CandlePrice(middlePrice):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	try:
		cur = dbConn.cursor()
		sql = "select start_price, end_price from candle_info order by num desc limit 49"
		#print(sql)
		cur.execute(sql)
		rows = cur.fetchall()
		middleTotalPrice = float(0)
		count = 0
		for row in rows:
			startPrice = float(row[0])
			endPrice = float(row[1])
			middleTotalPrice = middleTotalPrice + ((startPrice + endPrice) / 2)
			count = count + 1

		middleTotalPrice = middleTotalPrice + middlePrice
		candle50Price = float(middleTotalPrice / (count + 1))
	except:
		candle50Price = 0
	finally:
		cur.close()
		dbConn.close()
		print("50 CANDLE PRICE: " + str(candle50Price))
	return candle50Price

def _getChangeRateOfMiddlePrice(lastCandleDataNum, middlePrice):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "select middle_Price from candle_info where data_info_2_num = '" + str(lastCandleDataNum) + "'"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		lastMiddlePrice = float(row[0])

		if(lastMiddlePrice == 0):
			lastMiddlePrice = middlePrice

		changeRateOfMiddlePrice = float(((middlePrice - lastMiddlePrice) / lastMiddlePrice) * 100)

	finally:
		cur.close()
		dbConn.close()

	print("ChangeRateOfMiddlePrice: " + str(changeRateOfMiddlePrice))

	return changeRateOfMiddlePrice

def _getChangeRateOf15Candle(lastCandleDataNum, candle15Price):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "select 15candle_price from candle_info where data_info_2_num = '" + str(lastCandleDataNum) + "'"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		last15CandlePrice = float(row[0])

		if(last15CandlePrice == 0):
			last15CandlePrice = candle15Price

		changeRateOf15CandlePrice = float(((candle15Price - last15CandlePrice) / last15CandlePrice) * 100)

	finally:
		cur.close()
		dbConn.close()

	print("ChangeRateOf15CandlePrice: " + str(changeRateOf15CandlePrice))
	return changeRateOf15CandlePrice

def _getChangeRateOf50Candle(lastCandleDataNum, candle50Price):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "select 50candle_price from candle_info where data_info_2_num = '" + str(lastCandleDataNum) + "'"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		last50CandlePrice = float(row[0])

		if(last50CandlePrice == 0):
			last50CandlePrice = candle15Price

		changeRateOf50CandlePrice = float(((candle50Price - last50CandlePrice) / last50CandlePrice) * 100)

	finally:
		cur.close()
		dbConn.close()

	print("ChangeRateOf50CandlePrice: " + str(changeRateOf50CandlePrice))
	return changeRateOf50CandlePrice

def	_setCandlePrice(lastDataInfoNum, highestPrice, lowestPrice, startPrice, endPrice, candle15Price, candle50Price, middlePrice, changeRateOfMiddlePrice, changeRateOf15Candle, changeRateOf50Candle):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "insert into candle_info (data_info_2_num, highest_price, lowest_price, start_price, end_price, 15candle_price, 50candle_price, middle_price, change_rate_middle_price, change_rate_15cadle_price, change_rate_50cadle_price) values (" \
			  + str(lastDataInfoNum) + ", " + str(highestPrice) + ", " + str(lowestPrice) + ", " + str(startPrice) + ", " + str(endPrice) + ", " + str(candle15Price) + ", " + str(candle50Price) + ", " \
			  + str(middlePrice) + ", " + str(changeRateOfMiddlePrice) + ", " + str(changeRateOf15Candle) + ", " + str(changeRateOf50Candle) + ")"
		print(sql)
		cur.execute(sql)
		cur.connection.commit()

	finally:
		cur.close()
		dbConn.close()

	return

def _checkLastRowNum():
	global lastRowNum

	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)

	checkResult = True
	try:
		cur = dbConn.cursor()
		sql = "select max(num) from data_info_2"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = int(row[0])
		if(lastRowNum == rowNum):
			checkResult = False

		lastRowNum = rowNum
	except:
		checkResult = False
	finally:
		cur.close()
		dbConn.close()
	return checkResult

def _getGapRateStatus():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	checkStatus = True

	try:
		cur = dbConn.cursor()
		sql = "select gab_rate from data_info_2 order by num desc limit 10"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchall()
		for data in row:
			print(data[0])
			if(float(data[0]) < -1.5):
				checkStatus = False
				break
	except:
		checkStatus = False
	finally:
		cur.close()
		dbConn.close()
	return checkStatus

def _getUpbitPriceStatus():

	return True

def _getBinancePriceStatus():

	return True

def _buyEthereum():
	global checkTradingStatus
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		checkTradingStatus = 1
		inputFile = open("TradingHistory.txt", "a")
		cur = dbConn.cursor()
		sql = "select max(num), upbit_price from data_info_2"
		print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		ruwNum = str(row[0])
		buyPrice = str(row[1])

		inputFile.write("buy Ethereum : " + buyPrice + ", number: " + rowNum + "\n")
		checkTradingStatus = 2
	except:
		inputFile.write("CANNOT BUY ETHEREUM!!!\n")
		checkTradingStatus = 0
	finally:
		inputFile.close()
		cur.close()
		dbConn.close()

	return

def _sellEthereum():
	global checkTradingStatus

	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		checkTradingStatus = 3
		inputFile = open("TradingHistory.txt", "a")
		cur = dbConn.cursor()
		sql = "select max(num), upbit_price from data_info_2"
		print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		ruwNum = str(row[0])
		buyPrice = str(row[1])

		inputFile.write("sell Ethereum : " + buyPrice + ", number: " + rowNum + "\n")
		checkTradingStatus = 0
	except:
		inputFile.write("CANNOT SELL ETHEREUM!!!\n")
		checkTradingStatus = 2
	finally:
		inputFile.close()
		cur.close()
		dbConn.close()

	return

def _getLastGapRate():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "select max(num), gab_rate from data_info_2"
		print(sql)
		cur.execute(sql)
		row = cur.fetchone()
		gapRate = float(row[1])
	except:
		gapRate = float(0)
	finally:
		cur.close()
		dbConn.close()

	return gapRate

def _getUpbitData():
	url = "https://api.upbit.com/v1/orderbook"

	try:
		querystring = {"markets":"KRW-ETH"}
		response = requests.get(url, params=querystring)
		data_list = json.loads(response.text)
		currentPrice = data_list[0]["orderbook_units"][0]["bid_price"]
	except:
		currentPrice = ""

	return currentPrice

"""
def _runBinanceData():
	global checkBinanceThreading
	checkBinanceThreading = True
	print("runBinanceData")

	while(checkBinanceThreading == True):
		time.sleep(5)
		cPrice, cTime, cType = _getBinanceData()
		cUSDPrice = _getUSDTFromCoinmarketcapData()
		_setData(cPrice * cUSDPrice, cTime, "Binance", cType)
		if(checkBinanceThreading == False):
			break

	print("stop runBinanceData")
"""

def _getBinanceData():
	client = Client('',
					'')

	try:
		ticker = client.get_symbol_ticker(symbol = 'ETHUSDT')
		data_dumps = json.dumps(ticker)

		data_list = json.loads(data_dumps)
		currentPrice = data_list["price"]
	
	except:
		currentPrice = ""

	return currentPrice

def _getUSDTFromCoinmarketcapData():
	url = "https://api.coinmarketcap.com/v2/ticker/825/"

	try:
		response = requests.get(url)
		data_list = json.loads(response.text)
		usdtPrice = data_list["data"]["quotes"]["USD"]["price"]

	except:
		usdtPrice = ""

	return usdtPrice

def _getExchangeRateData():
	url = "https://www.koreaexim.go.kr/site/program/financial/ exchangeJSON?authkey=   &data=AP01"
	try:
		response = requests.get(url)
		data_list = json.loads(response.text)
	except:
		data_list = ""

	if(data_list == "" or len(data_list) == 0):
		lastUsdPrice = _getLastUsdPrice()
		return float(lastUsdPrice)

	for i in range(0, len(data_list)):
		if(data_list[i]["cur_unit"] == "USD"):
			usdPrice = data_list[i]["kftc_deal_bas_r"]
			usdPrice = usdPrice.replace(',', '')
			floatUsdPrice = float(usdPrice)
			return floatUsdPrice

	lastUsdPrice = _getLastUsdPrice()
	return float(lastUsdPrice)

def _insertDataQueue(type_name, time, upbitPrice, binancePrice, usdtPrice, usdPrice):
	global globalQueue
	global semaphore

	#print(upbitPrice)
	#print(binancePrice)
	#print(usdtPrice)
	#print(usdPrice)
	#print(type(upbitPrice))
	#print(type(binancePrice))
	#print(type(usdtPrice))
	#print(type(usdPrice))

	modifiedBinancePrice = usdtPrice * binancePrice * usdPrice
	gap = float(upbitPrice - modifiedBinancePrice)
	gapRate = float((gap / modifiedBinancePrice) * 100)
	print("PUT: " + str(type_name) + ", " + str(time) + ", " + str(upbitPrice) + ", " + str(modifiedBinancePrice) + ", " + str(usdPrice) + ", " + str(gap) + ", " + str(gapRate))

	semaphore.acquire()
	globalQueue.put("HANETER")
	globalQueue.put(str(type_name))
	globalQueue.put(str(time))
	globalQueue.put(str(upbitPrice))
	globalQueue.put(str(modifiedBinancePrice))
	globalQueue.put(str(usdPrice))
	globalQueue.put(str(gap))
	globalQueue.put(str(gapRate))
	semaphore.release()

	return

def _insertData():
	global globalQueue
	global checkInsertData
	global semaphore

	semaphore.acquire()
	if(globalQueue.empty() == True):
		currentTime = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		print("QUEUE IS EMPTY!! " + str(currentTime))
		semaphore.release()
		checkInsertData = checkInsertData + 1
		return

	checkSum = globalQueue.get()
	while(checkSum != "HANETER"):
		checkSum = globalQueue.get()
		if(globalQueue.empty() == True):
			print("ERROR QUEUE IS EMPTY!!")
			semaphore.release()
			checkInsertDat = checkInsertData + 1
			return
	queue1 = globalQueue.get()
	queue2 = globalQueue.get()
	queue3 = globalQueue.get()
	queue4 = globalQueue.get()
	queue5 = globalQueue.get()
	queue6 = globalQueue.get()
	queue7 = globalQueue.get()
	checkInsertData = 0
	semaphore.release()

	type_name =  str(queue1)
	time = str(queue2)
	upbitPrice = float(queue3)
	modifiedBinancePrice = float(queue4)
	usdPrice = float(queue5)
	gap = float(queue6)
	gapRate = float(queue7)

	print("GET: " + str(type_name) + ", " + str(time) + ", " + str(upbitPrice) + ", " + str(modifiedBinancePrice) + ", " + str(usdPrice) + ", " + str(gap) + ", " + str(gapRate))

	_setData(type_name, time, upbitPrice, modifiedBinancePrice, usdPrice, gap, gapRate)

	return

def	_setData(type_name, time, upbitPrice, modifiedBinancePrice, usdPrice, gap, gapRate):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "select * from type_info where type_name = '" + type_name + "'"
		#print(sql)
		cur.execute(sql)
		row = cur.fetchone()

		sql = "insert into data_info_2 (type, record_time, upbit_price, binance_price, exchange_rate, gab, gab_rate) values ("\
			  + str(row[0]) + ", '" + str(time) + "', " + str(upbitPrice) + ", " + str(modifiedBinancePrice) + ", " + str(usdPrice) + ", " + str(gap) + ", " + str(gapRate) + ")"
		print(sql)
		cur.execute(sql)
		cur.connection.commit()

	finally:
		cur.close()
		dbConn.close()

	return

"""
def _setData(price, time, exchange_info, crypto_type):
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "select * from exchange_info where name = '" + exchange_info + "'"
		print(sql)
		cur.execute(sql)
		row = cur.fetchone()

		sql = "insert into data_info (exchange_info_num, type, price, time) values (" + str(row[0]) + ", '" + crypto_type + "', " + str(price) + ", '" + str(time) + "')"
		print(sql)
		semaphore.acquire()
		cur.execute(sql)
		cur.connection.commit()
		semaphore.release()

	finally:
		cur.close()
		dbConn.close()
"""

def _getLastUsdPrice():
	dbConn = pymysql.connect (
		host = 'localhost',
		user = 'haneter',
		password = 'myfriend80',
		db = 'upbit',
		charset = 'utf8'
	)
	try:
		cur = dbConn.cursor()
		sql = "select exchange_rate from data_info_2 order by num desc"
		print(sql)
		cur.execute(sql)
		row = cur.fetchone()

	finally:
		cur.close()
		dbConn.close()

	return row[0]

def _runTestData():
	global checkTestThreading
	checkTestThreading = True
	print("runTestData")

	while(checkTestThreading == True):
		time.sleep(2)
		aa = _getExchangeRateData()
		print(aa)
		if(checkTestThreading == False):
			break

	print("stop runTestData")

def main():
	global checkUpbitThreading
	global checkRecordDataThreading
	global checkMakeCandleThreading
	global checkCheckStatusThreading
	global checkTradingThreading
	global checkTestThreading
	checkWhile = True

	th0 = threading.Thread(target=runUsdPrice)
	th0.start()

	while(checkWhile == True):
		print("My Program")
		print("1: Start to Get Upbit Data")
		print("2: Start to Record data into DB")
		print("3: Start to Make Candle")
		print("4: Start to Trading Ethereum")
		print("11: Stop to Get Upbit Data")
		print("12: Stop to Record data into DB")
		print("13: Stop to Make Candle")
		print("14: Stop to Trading Ethereum")
		print("9: EXIT")
		print("20: Start to Run Test")
		print("21: Stop to Run Test")
		userCmd = input("Please Choose Number: ")

		if(userCmd == '1'):
			print("userCmd is 1")
			th1 = threading.Thread(target=runUpbitData)
			th1.start()
		if(userCmd == '2'):
			print("userCmd is 2")
			th2 = threading.Thread(target=runRecordData)
			th2.start()
		if(userCmd == '3'):
			print("userCmd is 3")
			th3 = threading.Thread(target=runMakeCandle)
			th3.start()
		if(userCmd == '4'):
			print("userCmd is 4")
			th4 = threading.Thread(target=runTradingEthereum)
			th4.start()
		if(userCmd == '11'):
			print("userCmd is 11")
			checkUpbitThreading = False
		if(userCmd == '12'):
			print("userCmd is 12")
			checkRecordDataThreading = False
		if(userCmd == '13'):
			print("userCmd is 13")
			checkMakeCandleThreading = False
		if(userCmd == '14'):
			print("userCmd is 14")
			checkTradingThreading = False

		if(userCmd == '10'):
			print("userCmd is 10")
			th10 = threading.Thread(target=_runTestData)
			th10.start()
		if(userCmd == '11'):
			print("userCmd is 11")
			checkTestThreading = False
		if(userCmd == '9'):
			checkUpbitThreading = False
			checkRecordDataThreading = False
			checkCheckStatusThreading = False
			checkTradingThreading = False
			checkTestThreading = False
			checkWhile = False

	print("Exit Program")

if __name__ == "__main__":
	main()
