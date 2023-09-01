from fastapi import FastAPI, Body
import requests
import json
from typing import Dict
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import urllib.request
import mysql.connector
from cachetools import cached, TTLCache


cnx = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="",
    database="flight"
)


cursor = cnx.cursor()

app = FastAPI()
app.add_middleware(CORSMiddleware,allow_origins = ["*"],allow_credentials = True,allow_methods = ["*"],allow_headers = ["*"])
handler = Mangum(app)


shared_response = None


class RouteInfo(BaseModel):
    fromCityOrAirport: dict
    toCityOrAirport: dict
    travelDate: str

class SearchQuery(BaseModel):
    cabinClass: str
    paxInfo: dict
    routeInfos: list[RouteInfo]
    searchModifiers: dict

class SearchQ(BaseModel):
    searchQuery: SearchQuery



def AdtCounts():
    print("Enter the Number of Adults: ")
    result = int(input())
    if type(result) == int:
        adt = result
        return adt
    else:
        exit()
        
def ChdCounts():
    print("Enter the Number of Childs between 0 to 6 :")
    result = int(input())
    if type(result) == int and ( result in range(0,7)):
        chd = result
        return chd
    else:
        exit()

def InfCounts():
    print("Enter the Number of Infants between 0 to 6 :")
    result = int(input())
    if type(result) == int and ( result in range(0,7)):
        inf = result
        return inf
    else:
        exit()

def CabinClass():
    print("Please choose the cabin Class: ")
    print("Press 1 for Economy")
    print("Press 2 for Premium Economy")
    print("Press 3 for Business")
    print("Press 4 for First")
    Cabin = int(input("Enter Please: "))
    if Cabin == 1:
        Cabin = "ECONOMY"
        return Cabin
    elif Cabin == 2:
        Cabin = "PREMIUM_ECONOMY"
        return Cabin
    elif Cabin == 3:
        Cabin = "BUSINESS"
        return Cabin
    elif Cabin == 4:
        Cabin = "FIRST"
        return Cabin
    else:
        print("Wrong input! Please enter right number next time!")
        exit()

        
def TravelerInfo():
    TravelerInfo = {}
    TravelerInfo['Adult'] = AdtCounts()
    TravelerInfo['Child'] = ChdCounts()
    TravelerInfo['Infant'] = InfCounts()
    TravelerInfo['cabinclass'] = CabinClass()
    TravelerInfo['Source'] = input("Enter Source in Format: STR: ")
    TravelerInfo['Destination'] = input("Enter Destination in Format: STR: ")
    return TravelerInfo

#Extract SSR From Review
def extractSSR(review):
    res = review
    total_flight_routes = len(res["tripInfos"])
    total_price_routes = {}
    for i in range(total_flight_routes):
        total_stops = len(res["tripInfos"][i]["sI"])
        dict1 = {}
        for j in range(total_stops):
            converted_data = []
            converted_data.append(res["tripInfos"][i]["sI"][j]["ssrInfo"])
            dict1[j] = converted_data
        total_price_routes[i] = dict1
        dict1 = {}
    return total_price_routes
    
#Extract total price from review and Converts to USD
def extractTotalPrice(review):
    price = Price()
    totalPriceInfo = {}
    totalPriceInfo["totalFareDetail"] = {}
    totalPriceInfo["totalFareDetail"]["fC"] = {}
    totalPriceInfo["totalFareDetail"]["fC"]["BF"] = round(review["totalPriceInfo"]["totalFareDetail"]["fC"]["BF"] * price["conversion_rates"]["USD"] , 2)
    totalPriceInfo["totalFareDetail"]["fC"]["TF"] = round(review["totalPriceInfo"]["totalFareDetail"]["fC"]["TF"] * price["conversion_rates"]["USD"] , 2)
    totalPriceInfo["totalFareDetail"]["fC"]["NF"] = round(review["totalPriceInfo"]["totalFareDetail"]["fC"]["NF"] * price["conversion_rates"]["USD"] , 2)
    totalPriceInfo["totalFareDetail"]["fC"]["TAF"] = round(review["totalPriceInfo"]["totalFareDetail"]["fC"]["TAF"] * price["conversion_rates"]["USD"] , 2)
    totalPriceInfo["totalFareDetail"]["afC"] = {}
    totalPriceInfo["totalFareDetail"]["afC"]["TAF"] = {}
    totalPriceInfo["totalFareDetail"]["afC"]["TAF"]["AGST"] = round(review["totalPriceInfo"]["totalFareDetail"]["afC"]["TAF"]["AGST"] * price["conversion_rates"]["USD"] , 2)
    totalPriceInfo["totalFareDetail"]["afC"]["TAF"]["OT"] = round(review["totalPriceInfo"]["totalFareDetail"]["afC"]["TAF"]["OT"] * price["conversion_rates"]["USD"] , 2)
    totalPriceInfo["totalFareDetail"]["afC"]["TAF"]["YQ"] = round(review["totalPriceInfo"]["totalFareDetail"]["afC"]["TAF"]["YQ"] * price["conversion_rates"]["USD"] , 2)
    return totalPriceInfo




def Price():
    # Where USD is the base currency you want to use
    url = 'https://v6.exchangerate-api.com/v6/d5817a0261c0b5bfe85e5632/latest/INR'

    # Making our request
    response = requests.get(url)
    data = response.json()

    # Your JSON object
    return data

def INR_to_USD_SSR(res):
    price = Price()
    for key,value in res.items():
        for k,v in value.items():
            for i in v:
                for a,b in i.items():
                    for j in b:
                        for key,value in j.items():
                            if key == "amount":
                                j["amount"] = round(j["amount"] * price["conversion_rates"]["USD"] , 2)
    return res


def Price():
    # Where USD is the base currency you want to use
    url = 'https://v6.exchangerate-api.com/v6/d5817a0261c0b5bfe85e5632/latest/INR'

    # Making our request
    response = requests.get(url)
    data = response.json()

    # Your JSON object
    return data



# Load the airport JSON data
with open("AirportDataTJ.json",'r',encoding='utf-8') as file:
    airports_data = json.load(file)


# Configure the cache
cache = TTLCache(maxsize=1000, ttl=3600)  # Adjust the cache size and TTL as needed


@cached(cache)  # Apply caching to this function
def get_airports_data():
    return airports_data

@app.get("/autocomplete")
async def autocomplete_city(query: str):
    airports = get_airports_data()

    Matching = [airport for airport in airports if (query.lower() in airport["city"].lower() or query.lower() in airport["name"].lower() or query.lower() in airport["country"].lower() or query.lower() in airport["code"].lower() or query.lower() in airport["countrycode"])]
    return Matching



#Create Dynamic Search Schema for Multicity
@app.post("/create-dynamic-schema")
async def generate_schema(json_data: dict = Body(...)):
    global shared_response
    shared_response = json_data
    return json_data

#Search for Domestic or International Oneway
@app.get("/Oneway")
def OnewaySearch(cabinclass:str,adults:int,childs:int,infants:int,source:str,destination:str,traveldate:str,direct:bool,connecting:bool):
    payload = json.dumps({
        "searchQuery": {
            "cabinClass": cabinclass,
            "paxInfo": {
            "ADULT": adults,
            "CHILD": childs,
            "INFANT": infants 
            },
            
            "routeInfos": [
            {	
                "fromCityOrAirport": {
                "code": source
                },
                "toCityOrAirport": {
                "code": destination
                },
                "travelDate": traveldate
            }
            ],
            "searchModifiers": {
            "isDirectFlight": direct,
            "isConnectingFlight": connecting
            }
        }
        })
    url = "https://apitest.tripjack.com/fms/v1/air-search-all"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    final = requests.request("POST", url, headers=headers, data=payload)
    if final.ok:
        res = final.json()
        result = {}
        result['searchResult'] = {}
        result['searchResult']['tripInfos'] = {}
        result['searchResult']['tripInfos']['ONWARD'] = []
        total = len(res['searchResult']['tripInfos']['ONWARD'])
        data = {}
        highprice = 0
        for i in range(total):
            data['sI'] = []
            data['sI'].append(res['searchResult']['tripInfos']['ONWARD'][i]['sI'])
            data['totalPriceList'] = []
            flight = res['searchResult']['tripInfos']['ONWARD'][i]
            totalprices = len(flight['totalPriceList'])
            maxprice = 0
            for j in range(totalprices):
                fareid = flight['totalPriceList'][j]['fareIdentifier']
                if fareid == "PUBLISHED":
                    if flight['totalPriceList'][j]['fd']['ADULT']['fC']['TF'] > maxprice:
                        highprice = flight['totalPriceList'][j]
            data['totalPriceList'].append(highprice)
            result['searchResult']['tripInfos']['ONWARD'].append(data)
            data = {}
        return result
    
    
#Search for Domestic or International Return
@app.get("/Return")
def ReturnSearch(cabinclass:str,adults:int,childs:int,infants:int,source:str,destination:str,traveldate:str,returndate:str,direct:bool,connecting:bool):
    payload = json.dumps({
        "searchQuery": {
            "cabinClass": cabinclass,
            "paxInfo": {
            "ADULT": adults,
            "CHILD": childs,
            "INFANT": infants 
            },
            
            "routeInfos": [
            {	
                "fromCityOrAirport": {
                "code": source
                },
                "toCityOrAirport": {
                "code": destination
                },
                "travelDate": traveldate
            },
            {	
                "fromCityOrAirport": {
                "code": destination
                },
                "toCityOrAirport": {
                "code": source
                },
                "travelDate": returndate
            }
            ],
            "searchModifiers": {
            "isDirectFlight": direct,
            "isConnectingFlight": connecting
            }
        }
        })
    url = "https://apitest.tripjack.com/fms/v1/air-search-all"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    final = requests.request("POST", url, headers=headers, data=payload)
    if final.ok:
        res = final.json()
        result = {}
        result['searchResult'] = {}
        result['searchResult']['tripInfos'] = {}
        result['searchResult']['tripInfos']['RETURN'] = []
        result['searchResult']['tripInfos']['ONWARD'] = []
        totalreturn = len(res['searchResult']['tripInfos']['RETURN'])
        totalonward = len(res['searchResult']['tripInfos']['ONWARD'])
        datao = {}
        datar = {}
        for i in range(totalreturn):
            datar['sI'] = []
            datar['sI'].append(res['searchResult']['tripInfos']['RETURN'][i]['sI'])
            datar['totalPriceList'] = []
            flight = res['searchResult']['tripInfos']['RETURN'][i]
            totalprices = len(flight['totalPriceList'])
            maxprice = 0
            for j in range(totalprices):
                fareid = flight['totalPriceList'][j]['fareIdentifier']
                if fareid == "PUBLISHED":
                    if flight['totalPriceList'][j]['fd']['ADULT']['fC']['TF'] > maxprice:
                        highprice = flight['totalPriceList'][j]
            datar['totalPriceList'].append(highprice)
            result['searchResult']['tripInfos']['RETURN'].append(datar)
            datar = {}
        for i in range(totalonward):
            datao['sI'] = []
            datao['sI'].append(res['searchResult']['tripInfos']['ONWARD'][i]['sI'])
            datao['totalPriceList'] = []
            flight = res['searchResult']['tripInfos']['ONWARD'][i]
            totalprices = len(flight['totalPriceList'])
            maxprice = 0
            for j in range(totalprices):
                fareid = flight['totalPriceList'][j]['fareIdentifier']
                if fareid == "PUBLISHED":
                    if flight['totalPriceList'][j]['fd']['ADULT']['fC']['TF'] > maxprice:
                        highprice = flight['totalPriceList'][j]
            datao['totalPriceList'].append(highprice)
            result['searchResult']['tripInfos']['ONWARD'].append(datao)
            datao = {}
        return result

#Search for Domestic or International Multicity
@app.get("/Multicity")
def Search():
    global shared_response
    response = json.dumps(shared_response)
    url = "https://apitest.tripjack.com/fms/v1/air-search-all"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    if shared_response:
        final = requests.request("POST", url, headers=headers, data=response)
        res = final.json()
        return res


#Review Selected Flight
@app.post("/Review Flight")
def Review(priceIds:list):
    url = "https://apitest.tripjack.com/fms/v1/review"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"priceIds": priceIds})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        SSR_USD = extractSSR(res)
        SSR_USD = INR_to_USD_SSR(SSR_USD)
        Total_USD = extractTotalPrice(res)
        return res,SSR_USD,Total_USD


    

#Get Fare Rule of Selected Flight
@app.post("/Fare Rule")
def Farerule(id:str,flowtype:str):
    url = "https://apitest.tripjack.com/fms/v1/farerule"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"id": id,"flowType": flowtype})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res

#Get Seat Map of selected flight
@app.post("/Seat Map")
def Seatmap(bookingid:str):
    url = "https://apitest.tripjack.com/fms/v1/seat"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"bookingId": bookingid})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res

#Create booking/Hold Itenary
@app.post("/Booking")
def Booking(payload: dict):
    url = "https://apitest.tripjack.com/oms/v1/air/book"
    headers = {
        'Content-Type': 'application/json',
        'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        return response_data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#Fare Validate after Blocking
@app.post("/Fare Validate")
def Validate(bookingid:str):
    url = "https://apitest.tripjack.com/oms/v1/air/fare-validate"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"bookingId": bookingid})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res

#Confirm Booking after Holding
@app.post("/Confirm Book")
def Confirm(bookingid:str,amount:float):
    url = "https://apitest.tripjack.com/oms/v1/air/confirm-book"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"bookingId": bookingid,"paymentInfos": [{"amount": amount}]})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        '''response_string = json.dumps(res)
        insert_query = """
            INSERT INTO json_responses (response) VALUES (%s)
        """
        cursor.execute(insert_query, (response_string,))
        cnx.commit()'''
        return res
#Get Booking Details
@app.post("/Booking Details")
def Bookingdetails(bookingid:str):
    url = "https://apitest.tripjack.com/oms/v1/booking-details"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"bookingId": bookingid})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res
#Get Booking Details with Pax Pricing
@app.post("/Booking Details with Pax Pricing")
def Bookingdetails(bookingid:str):
    url = "https://apitest.tripjack.com/oms/v1/booking-details"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"bookingId": bookingid,"requirePaxPricing": True})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res
#Release PNR 
@app.post("/Release PNR")
def ReleasePNR(bookingid:str,pnrs:list):
    url =  "https://apitest.tripjack.com/oms/v1/air/unhold"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"bookingId":bookingid,"pnrs":pnrs})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res
#Get User Balance
@app.post("/User Balance")
def Userbalance(apikey:str):
    url =  "https://apitest.tripjack.com/ums/v1/user-detail" 
    headers = {'Content-Type': 'application/json','apikey': apikey}
    payload = {}
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res
    
@app.on_event("shutdown")
def shutdown_event():
    cursor.close()
    cnx.close()

# Load the TJ_hotel_nationality JSON data
with open("TJ_hotel_nationality.json",'r',encoding='utf-8-sig') as file: #encoding='utf-8'
    nationality_data = json.load(file)

# Load the TJ_hotel_city JSON data
with open("TJ_hotel_city.json",'r',encoding='utf-8') as file:
    city_data = json.load(file)

# Configure the nationality cache
cache_nationality = TTLCache(maxsize=100, ttl=3600)  # Adjust the cache size and TTL as needed

# Configure the city cache
cache_city = TTLCache(maxsize=5000, ttl=3600)  # Adjust the cache size and TTL as needed

@cached(cache_nationality)  # Apply caching to this function
def get_nationality_data():
    return nationality_data


@cached(cache_city)  # Apply caching to this function
def get_city_data():
    return city_data


@app.get("/autocomplete_nationality")
async def autocomplete_nationality(query: str):

    nationality = get_nationality_data()

    Matching_nationality = [MN for MN in nationality if (query.lower() in MN["countryname"].lower() or query.lower() in MN["name"].lower() or query.lower() in MN["countryid"].lower() or query.lower() in MN["code"].lower() or query.lower() in MN["isocode"] or query.lower() in MN["dial_code"])]
    return Matching_nationality



@app.get("/autocomplete_city")
async def autocomplete_city(query: str):
    city = get_city_data()
    Matching_city = [MC for MC in city if (query.lower() in MC["countryName"].lower() or query.lower() in MC["cityName"].lower() or query.lower() in MC["type"].lower())]
    return Matching_city
    

@app.get("/Exchange rates")
async def Exchange_rates(amount:float):
    # Where USD is the base currency you want to use
    url = 'https://v6.exchangerate-api.com/v6/d5817a0261c0b5bfe85e5632/latest/INR'
    url1 = 'https://v6.exchangerate-api.com/v6/d5817a0261c0b5bfe85e5632/pair/INR/USD/'
    AMOUNT = amount
    url1 += str(AMOUNT)

    # Making our request
    response = requests.get(url1)
    data = response.json()

    # Your JSON object
    return data



#Dynamic Seacrh Schema
@app.get("/SearchSchema")
def SearchSchema():
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    
    url = "https://apitest.tripjack.com/hms/v1/hotel-searchquery-list"
    
    search = {}
    search['searchQuery'] = {}
    search['searchQuery']["checkinDate"] = input("Enter Checkin date in format: YYYY-MM-DD")
    search['searchQuery']["checkoutDate"] = input("Enter Checkout date in format: YYYY-MM-DD")
    search['searchQuery']["roomInfo"] = []
    rooms = int(input("Enter Rooms: "))
    room = {}
    for i in range(rooms): 
        room["numberOfAdults"] = int(input("Enter No. of Adults: "))
        room["numberOfChild"] = int(input("Enter No. of Childs: "))
        if room["numberOfChild"] > 0:
            room["childAge"] = []
            for i in range(room["numberOfChild"]):
                age = int(input("Enter Age: "))
                room["childAge"].append(age)
        search['searchQuery']["roomInfo"].append(room)
        room = {}
    search['searchQuery']["searchCriteria"] = {}
    search['searchQuery']["searchCriteria"]["city"] = input("Enter City Code: ")
    search['searchQuery']["searchCriteria"]["currency"] = input("Enter Currency: ")
    search['searchQuery']["searchCriteria"]["nationality"] = input("Enter Nationality code: ")
    search['searchQuery']["searchPreferences"] = {}
    search['searchQuery']["searchPreferences"]['ratings'] = []
    rating = int(input("Enter rating in range: 0 to 5"))
    for i in range(rating+1):
        search['searchQuery']["searchPreferences"]['ratings'].append(i)
    search['searchQuery']["searchPreferences"]['fsc'] = True
    search['sync'] = True
    payload = json.dumps(search)
    response = requests.request("POST", url, headers=headers, data=payload)
    res = json.loads(response.text)
    return res


#Searchschema = SearchSchema()

@app.get("/SearchID")
def SearchID(search:str):
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }

    '''for key,value in Response.items():
        if key == "searchIds":
            res = value[0]
    '''
    
    url = "https://apitest.tripjack.com/hms/v1/hotel-search"
    payload =  json.dumps({"searchId": search})
    response = requests.request("POST", url, headers=headers, data=payload)
    res = json.loads(response.text)
    return res

#Searchid = SearchID(input("Enter Search ID: "))




@app.get("/HotelDetails")
def Details(searchid:str):
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }

    '''
    ids = []
    count = int(B['searchResult']['size'])
    for i in range(count):
        for key,value in B['searchResult']['his'][i].items():
            if key == "id":
                ids.append(value)
    '''
    url = "https://apitest.tripjack.com/hms/v1/hotelDetail-search"
    payload = json.dumps({"id": searchid})
    response = requests.request("POST", url, headers=headers, data=payload)
    res = json.loads(response.text)
    return res


#HotelDetail = Details(input("Enter Hotel Search ID: "))




@app.get("/CancellationPolicy")
def CancellationPolicy(hotelid:str,optionid:str):
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    
    url = "https://apitest.tripjack.com/hms/v1/hotel-cancellation-policy"
    
    '''
    hotelid = C["hotel"]["id"]
    optionid = []
    length = len(C["hotel"]["ops"])
    for i in range(length):
        optionid.append(C["hotel"]["ops"][i]["id"])
    '''
    
    
    
    payload = json.dumps({"id": hotelid,"optionId": optionid})
    
    response = requests.request("POST", url, headers=headers, data=payload)
    res = json.loads(response.text)
    return res

#Cancellation = CancellationPolicy(input("Enter Hotel ID: "),input("Enter Option ID: "))


@app.get("/Review")
def Review(hotelid:str,optionid:str):
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    url = "https://apitest.tripjack.com/hms/v1/hotel-review"
    '''
    hotelid = C["hotel"]["id"]
    optionid = []
    length = len(C["hotel"]["ops"])
    for i in range(length):
        optionid.append(C["hotel"]["ops"][i]["id"])
    '''
    payload = json.dumps({"hotelId": hotelid,"optionId": optionid})
    response = requests.request("POST", url, headers=headers, data=payload)
    res = json.loads(response.text)
    return res



@app.get("/Hold Booking")
def Hold(bookingid:str):
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }

    url = "https://apitest.tripjack.com/oms/v1/hotel/book"
    hold = {}
    hold["bookingId"] = bookingid
    hold["roomTravellerInfo"] = []
    rooms = int(input())
    adults = int(input())
    childs = int(input())
    for i in range(rooms):
        info = {}
        info["travellerInfo"] = []

