import pymysql
import time
import datetime as dt
import threading

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

		currentStatus = _checkCurrentStatus()

		lastDataNum, lastTime, lastUpbitPrice, lastBinancePrice, lastExchangeRate, lastGap, lastGapRate = _getLastPrice()

		lastCandleNum, lastCandleDataNum, lastCandleHighestPrice, lastCandleLowestPrice, lastCandleStartPrice, lastCandleEndPrice, \
		lastCandle15CandlePrice, lastCandle50CandlePrice, lastCandleMiddlePrice, lastCandleChangeRate15Candle, \
		lastCandleChangeRate50Candle, lastCandleChangeRateMiddle =  _getLastCandlePrice()

		_getCandlePrice()

		if(currentStatus == 1):
			print("Normal Down Status")
		elif(currentStatus == 2):
			print("Normal Up Status")
		elif(currentStatus == 3):
			print("Normal Equal Status")
		elif(currentStatus == 4):
			print("Abnormal Down Status")
		elif(currentStatus == 5):
			print("Abnormal Up Status")
		elif(currentStatus == 6):
			print("Abnormal Equal Status")
		elif(currentStatus == 0):
			print("Error Return")
		else:
			print("Unknown Value: " + str(currentStatus))


		analResult = _analPrice(currentStatus)
		if(analResult==1):
			print("Need to Buy")
		elif(analResult==2): 
			print("Need to Sell")
		elif(analResult==3):
			print("Need to Pending")


	return

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
			rowMiddlePrice[count] = float(row[0])
			rowChangeRateMiddlePrice[count] = float(row[1])
			if(rowChangeRateMiddlePrice[count] >= 1 or rowChangeRateMiddlePrice[count] <= -1):
				checkAbnormal = True
			count = count + 1

		if(checkAbnormal == False):
			if(rowMiddlePrice[0] > rowMiddlePrice[count - 1]):
				returnValue = 1	
			elif(rowMiddlePrice[0] < rowMiddlePrice[count - 1]):
				returnValue = 2
			else
				returnValue = 3
		elif(checkAbnormal == True):
			if(rowMiddlePrice[0] > rowMiddlePrice[count - 1]):
				returnValue = 4
			elif(rowMiddlePrice[0] < rowMiddlePrice[count - 1]):
				returnValue = 5
			else
				returnValue = 6

	except:
		returnValue = 0
	finally:
		cur.close()
		dbConn.close()

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

def _checkCurrentStatus():
	return

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
		sql = "select * from candle_info order by num desc limit 1"
		cur.execute(sql)
		row = cur.fetchone()
		rowNum = int(row[0])
		rowDataNum = int(row[1])
		rowHighestPrice = float(row[2])
		rowLowestPrice = float(row[3])
		rowStartPrice = float(row[4])
		rowEndPrice = float(row[5])
		row15CandlePrice = float(row[6])
		row50CandlePrice = float(row[7])
		rowMiddlePrice = float(row[8])
		rowChangeRateMiddlePrice = float(row[9])
		rowChangeRate15CandlePrice = float(row[10])
		rowChangeRate50CandlePrice = float(row[11])
	except:
		rowNum = 0
		rowDataNum = 0
		rowHighestPrice = 0
		rowLowestPrice = 0
		rowStartPrice = 0
		rowEndPrice = 0
		row15CandlePrice = 0
		row50CandlePrice = 0
		rowMiddlePrice = 0
		rowChangeRateMiddlePrice = 0
		rowChangeRate15CandlePrice = 0
		rowChangeRate50CandlePrice = 0
	finally:
		cur.close()
		dbConn.close()
		print("Last Candle Price: " + str(rowNum) + ", " + str(rowDataNum) + ", " +  str(rowHighestPrice) + ", " + \
			str(rowLowestPrice) + ", " + str(rowStartPrice) + ", " + str(rowEndPrice) + ", " + str(row15CandlePrice) + ", " + \
			str(row50CandlePrice) + ", " + str(rowMiddlePrice) + ", " + str(rowChangeRateMiddlePrice) + ", " + str(rowChangeRate15CandlePrice) + ", " + \
			str(rowChangeRate50CandlePrice))

	return rowNum, rowDataNum, rowHighestPrice, rowLowestPrice, rowStartPrice, rowEndPrice, row15CandlePrice, row50CandlePrice, rowMiddlePrice, rowChangeRateMiddlePrice, rowChangeRate15CandlePrice, rowChangeRate50CandlePrice

def _analPrice(currentStatus):
	if(currentStatus == 1):
		print("Normal Down Status")
	elif(currentStatus == 2):
		print("Normal Up Status")
	elif(currentStatus == 3):
		print("Normal Equal Status")
	elif(currentStatus == 4):
		print("Abnormal Down Status")
	elif(currentStatus == 5):
		print("Abnormal Up Status")
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

		if(userCmd == '1'):
			print("userCmd is 1")
			th1 = threading.Thread(target = runTradingEthereum)
			th1.start()

		if(userCmd == '9'):
			checkTradingEthereum = False
			checkWhile = False

	print("Exit Program")

if __name__ == "__main__"
	main()
