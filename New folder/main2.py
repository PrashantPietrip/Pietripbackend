from fastapi import FastAPI
import requests
import json
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
import urllib.request

app = FastAPI()
app.add_middleware(CORSMiddleware,allow_origins = ["*"],allow_credentials = True,allow_methods = ["*"],allow_headers = ["*"])
handler = Mangum(app)





@app.get("/SearchSchema")
def SearchSchema(checkindate: str, checkoutdate: str, rooms: str, adults: str, child: str, city: str, currency: str, nationality: str):
    headers = {
        'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': '*'
    }

    url = "https://apitest.tripjack.com/hms/v1/hotel-searchquery-list"

    search = {}
    search['searchQuery'] = {}
    search['searchQuery']["checkinDate"] = checkindate
    search['searchQuery']["checkoutDate"] = checkoutdate
    search['searchQuery']["roomInfo"] = []
    rooms = int(rooms)
    adults = int(adults)
    child = int(child)
    ApR = (adults // rooms)
    CpR = (child // rooms)
    
    for _ in range(rooms): 
        room = {}
        room["numberOfAdults"] = ApR
        adults -= ApR
        room["numberOfChild"] = CpR
        child -= CpR
        if room["numberOfChild"] > 0:
            room["childAge"] = []
            for _ in range(room["numberOfChild"]):
                age = 11
                room["childAge"].append(age)
        search['searchQuery']["roomInfo"].append(room)

    for i in search['searchQuery']["roomInfo"]:
        if adults > 0:
            i["numberOfAdults"] = 1 + i["numberOfAdults"]
            adults -= 1
    for i in search['searchQuery']["roomInfo"]:
        if child > 0:
            i["numberOfChild"] = 1 + i["numberOfChild"]
            i["childAge"].append(11)
            child -= 1
    
    search['searchQuery']["searchCriteria"] = {}
    search['searchQuery']["searchCriteria"]["city"] = city
    search['searchQuery']["searchCriteria"]["currency"] = currency
    search['searchQuery']["searchCriteria"]["nationality"] = nationality
    search['searchQuery']["searchPreferences"] = {}
    search['searchQuery']["searchPreferences"]['ratings'] = [1, 2, 3, 4, 5]
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