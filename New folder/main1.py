from fastapi import FastAPI
import requests
import json
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
import urllib.request

#Airport data url

airport = 'https://raw.githubusercontent.com/Aakaaaassh/SQL/main/airport.json'



def Triptype():
    print("Enter trip type: ")
    print("1) Domestic (One way)")
    print("2) Domestic (Return)")
    print("3) International (One Way)")
    print("4) International (Return)")
    result = int(input("Enter 1,2,3 or 4: "))
    if result == 1:
        trip = "D1"
        return trip
    elif result == 2:
        trip = "D2"
        return trip
    elif result == 3:
        trip = "I1"
        return trip
    elif result == 4:
        trip = "I2"
        return trip
    else:
        exit()
    

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

def PCType():
    print("Enter the class type:")
    print("1)Economy")
    print("2)Business")
    print("3)Premium Economy")
    result = int(input("Enter 1,2 or 3: "))
    if type(result) == int:
        if result == 1:
            PC = "EC"
            return PC
        elif result == 2:
            PC = "BU"
            return PC
        elif result == 3:
            PC = "PE"
            return PC
        else:
            exit()

'''SRC = input()
DES = input()
ddate = input()
Adt = AdtCounts()
Chd = ChdCounts()
Inf = InfCounts()'''


app = FastAPI()
app.add_middleware(CORSMiddleware,allow_origins = ["*"],allow_credentials = True,allow_methods = ["*"],allow_headers = ["*"])
handler = Mangum(app)

headers = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin':'*',
  'Access-Control-Allow-Headers':'Content-Type,Authorization',
  'Access-Control-Allow-Methods':'*'
}

Aid = "3731123"
token = "8375d56adf6e2c0956b13c8fece9c23e"

url = "http://stage1.ksofttechnology.com/api/FSearch"


@app.get("/")
def Hello ():
    return {"Hello"}

@app.get("/OneWay")
def OneWay(SRC:str,DES:str,ddate:str,Adt:int,Chd:int,Inf:int):
    

    Oneway = json.dumps({
        "Trip": "D1",
        "Adt": Adt,
        "Chd": Chd,
        "Inf": Inf,
        "Sector": [
            {
                "Src": SRC,
                "Des": DES,
                "DDate": ddate
            }
        ],
        "PF": "",
        "PC": "",
        "Routing": "ALL",
        "Ver": "1.0.0.0",
        "Auth": {
          "AgentId": Aid,
          "Token": token
        },
        "Env": "D",
        "Module": "B2B",
        "OtherInfo": {
          "PromoCode": "KAF2022",
          "FFlight": "",
          "FareType": "",
          "TraceId": "",
          "IsUnitTesting": False,
          "TPnr": False
        }
      })
    response = requests.request("POST", url, headers=headers, data=Oneway)
    WF = []
    res = json.loads(response.text)
    flights = res["Schedules"][0]
    for flight in flights:
        Sec = flight["OI"]["Security"]
        seat = flight["Seat"]
        Departtime = flight["DDate"][11:16]
        Arrivaltime = flight["ADate"][11:16]
        DepartDate = flight["DDate"][:10]
        ArrivalDate = flight["ADate"][:10]
        Rate = round(flight["Fare"]["GrandTotal"]/85,2)
        flight["FRate"] = Rate
        flight["Departtime"] = Departtime
        flight["Arrivaltime"] = Arrivaltime
        flight["DepartDate"] = DepartDate
        flight["ArrivalDate"] = ArrivalDate
        if Sec == "NA" and seat < 1:
            continue
        else:
            WF.append(flight)
    response = {}
    for key,value in res.items():
        if key == "Schedules":
            continue
        else:
            response[key] = value
    response["Schedules"] = WF

    return response

@app.get("/RoundTrip")
def RoundTrip(SRC:str,DES:str,ddate:str,ReturnDate:str,Adt:int,Chd:int,Inf:int):
    Round = json.dumps({
      "Trip": "D2",
      "Adt": Adt,
      "Chd": Chd,
      "Inf": Inf,
      "Sector": [
        {
          "Src": SRC,
          "Des": DES,
          "DDate": ddate
        },
        {
          "Src": DES,
          "Des": SRC,
          "DDate": ReturnDate
        }
      ],
      "PF": "",
      "PC": "",
      "Routing": "ALL",
      "Ver": "1.0.0.0",
      "Auth": {
        "AgentId": Aid,
        "Token": token
      },
      "Env": "D",
      "Module": "B2B",
      "OtherInfo": {
        "PromoCode": "KAF2022",
        "FFlight": "",
        "FareType": "",
        "TraceId": "",
        "IsUnitTesting": False,
        "TPnr": False
      }
    })
    response = requests.request("POST", url, headers=headers, data=Round)
    WF = []
    res = json.loads(response.text)
    flights = res["Schedules"][0]
    for flight in flights:
        Sec = flight["OI"]["Security"]
        seat = flight["Seat"]
        Departtime = flight["DDate"][11:16]
        Arrivaltime = flight["ADate"][11:16]
        DepartDate = flight["DDate"][:10]
        ArrivalDate = flight["ADate"][:10]
        flight["Departtime"] = Departtime
        flight["Arrivaltime"] = Arrivaltime
        flight["DepartDate"] = DepartDate
        flight["ArrivalDate"] = ArrivalDate
        if Sec == "NA" and seat < 1:
            continue
        else:
            WF.append(flight)
    response = {}
    for key,value in res.items():
        if key == "Schedules":
            continue
        else:
            response[key] = value
    response["Schedules"] = WF

    return response



@app.get("/Airport")
def Airport():
    with urllib.request.urlopen(airport) as url:
        data = json.loads(url.read().decode())
        return data

