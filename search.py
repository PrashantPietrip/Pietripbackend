import requests
import json
from fastapi import FastAPI, Body
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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


# Load the airport JSON data
with open("AirportDataTj.json",'r',encoding='utf-8') as file:
    airports_data = json.load(file)


# Configure the cache
cache = TTLCache(maxsize=100, ttl=3600)  # Adjust the cache size and TTL as needed


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
    res = final.json()
    return res
    
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
    res = final.json()
    return res

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
@app.post("/Review")
def Review(priceIds:list):
    url = "https://apitest.tripjack.com/fms/v1/review"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    payload = json.dumps({"priceIds": priceIds})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res

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
def Booking(json_data: dict = Body(...)):
    url = "https://apitest.tripjack.com/oms/v1/air/book"
    headers = {'Content-Type': 'application/json','apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22'}
    response = requests.request("POST", url, headers=headers, data=json_data)
    if response.ok:
        res = response.json()
        '''response_string = json.dumps(res)
        insert_query = """
            INSERT INTO json_responses (response) VALUES (%s)
        """
        cursor.execute(insert_query, (response_string,))
        cnx.commit()'''
        return res
    
#Fare Valiodate after Blocking
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






        




    




