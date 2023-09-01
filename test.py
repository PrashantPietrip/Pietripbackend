from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
from mangum import Mangum
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional,Dict
import os
from dotenv import load_dotenv
import bcrypt
import mysql.connector
from mysql.connector import connect, Error
from cachetools import cached, TTLCache
from pyCoinPayments import CryptoPayments 
import secrets
import string 
import urllib


load_dotenv()


SECRET_KEY = os.getenv("FA_KEY")  # import this from your config or environment
TJ_KEY = os.getenv("TJ_KEY")
ER_KEY  = os.getenv("ER_KEY")
API_KEY = os.getenv("CP_KEY")
IPN_SECRET = os.getenv("IPN_SECRET")
MERCHANT_ID = os.getenv("MERCHANT_ID")
API_SECRET = os.getenv("CP_SECRET_KEY")
ALGORITHM = "HS256" 
IPN_URL = ""

app = FastAPI()
app.add_middleware(CORSMiddleware,allow_origins = ["*"],allow_credentials = True,allow_methods = ["*"],allow_headers = ["*"])
handler = Mangum(app)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="Login token")

class IPNURL():
    def __init__(self,ipn_url,ipntype,ipnsecret,merchantid):
        self.ipn_url = ipn_url
        self.ipn_version = 1.0
        self.ipn_type = ipntype
        self.ipn_mode = 'hmac'
        self.ipn_id = ipnsecret
        self.merchant = merchantid
        self.format = 'json'
        self.url = 'https://www.coinpayments.net/api.php'

    def generate_txn_id(length=128):
        characters = string.ascii_letters + string.digits + '-'
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def createHmac(self, **params):
        """ Generate an HMAC based upon the url arguments/parameters
            
            We generate the encoded url here and return it to Request because
            the hmac on both sides depends upon the order of the parameters, any
            change in the order and the hmacs wouldn't match
        """
        encoded = urllib.parse.urlencode(params).encode('utf-8')
        return encoded, hmac.new(bytearray(self.ipn_id, 'utf-8'), encoded, hashlib.sha512).hexdigest()

    def Request(self, request_method, **params):
        """ The basic request that all API calls use
            the parameters are joined in the actual api methods so the parameter
            strings can be passed and merged inside those methods instead of the 
            request method. The final encoded URL and HMAC are generated here
        """
        encoded, sig = self.createHmac(**params)

        headers = {'hmac': sig}

        if request_method == 'get':
            req = urllib.request.Request(self.url, headers=headers)
        elif request_method == 'post':
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            req = urllib.request.Request(self.url, data=encoded, headers=headers)

        try:
            response      = urllib.request.urlopen(req)
            status_code   = response.getcode()
            response_body = response.read()

            response_body_decoded = json.loads(response_body) #decode Json to dictionary

            response_body_decoded.update(response_body_decoded['result']) #clean up dictionary, flatten "result" key:value pairs to parent dictionary
            response_body_decoded.pop('result', None) #remove the flattened dictionary
            
        except urllib.error.HTTPError as e:
            status_code   = e.getcode()
            response_body = e.read()

        return response_body_decoded

    def createTransaction(self, params=None):
        """ Creates a transaction to give to the purchaser
            https://www.coinpayments.net/apidoc-create-transaction
        """
        params.update({'cmd':'create_transaction',
                       'ipn_url':self.ipn_url,
                       'key':self.publicKey,
                       'version': self.version,
                       'format': self.format}) 
        return self.Request('post', **params)

class User(BaseModel):
    email: str
    password: str
    disabled: Optional[bool] = False

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

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
    



def Price():
    # Where USD is the base currency you want to use
    url = 'https://v6.exchangerate-api.com/v6/' + ER_KEY + '/latest/INR'

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

#Extract total price from review and Converts to USD
def extractTotalPrice(B):
    review = B
    price = Price()
    totalPriceInfo = {}
    totalPriceInfo["totalFareDetail"] = {}
    totalPriceInfo["totalFareDetail"]["fC"] = {}
    for key,value in review["totalPriceInfo"]["totalFareDetail"]["fC"].items():
        totalPriceInfo["totalFareDetail"]["fC"][key] = {}
        totalPriceInfo["totalFareDetail"]["fC"][key] = round(value * price["conversion_rates"]["USD"] , 2)
    totalPriceInfo["totalFareDetail"]["afC"] = {}
    totalPriceInfo["totalFareDetail"]["afC"]["TAF"] = {}
    for key,value in review["totalPriceInfo"]["totalFareDetail"]["afC"]["TAF"].items():
        totalPriceInfo["totalFareDetail"]["afC"]["TAF"][key] = {}
        totalPriceInfo["totalFareDetail"]["afC"]["TAF"][key] = round(value * price["conversion_rates"]["USD"] , 2)
    return totalPriceInfo

#Convert Seat Prices to USD
def Seatmap_USD(Seatmap):
    price = Price()
    length = len(Seatmap["tripSeatMap"]["tripSeat"])
    #print(length)
    for keys,values in Seatmap["tripSeatMap"]["tripSeat"].items():
        #print(keys)
        for  i,j in values.items():
            #print(i)
            if i == "sInfo":
                for items in j:
                    #print(items)
                    for infos,prices in items.items():
                        if infos == "amount":
                            items[infos] = round(prices * price["conversion_rates"]["USD"] , 2)
    return Seatmap




def create_access_token(data: dict):
    SECRET_KEY = os.getenv("FA_KEY")
    # You should implement your token creation here
    # This is just an illustrative example.
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return token

def authenticate_user(email: str, password: str):
    cnx = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="users"
    )

    cursor = cnx.cursor(dictionary=True)
    cursor.execute('SELECT * FROM credentials WHERE email = %s', (email,))

    user = cursor.fetchone()

    cnx.close()

    if not user:
        return False
    
    if not pwd_context.verify(password, user['password']):
        return False

    return user

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    return token_data




@app.post("/Create User")
def create_user(email: str, password: str):
    # Hash the password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Establish a connection to MySQL
    cnx = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="users"
    )

    cursor = cnx.cursor()

    # Insert the user into the 'users' table
    cursor.execute('''
        INSERT INTO credentials (email, password) VALUES (%s, %s)
    ''', (email, hashed.decode('utf-8')))

    cnx.commit()

    # Close the connection
    cnx.close()
    return {"result": "Account Created"}


@app.post("/Login token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user['email']})

    return {"access_token": access_token, "token_type": "bearer"}



@app.get("/users/me")
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    return current_user


# Load the airport JSON data
with open("AirportDataTJ.json",'r',encoding='utf-8') as file:
    airports_data = json.load(file)


# Configure the cache
cache = TTLCache(maxsize=1000, ttl=3600)  # Adjust the cache size and TTL as needed


@cached(cache)  # Apply caching to this function
def get_airports_data():
    return airports_data

# @app.post("/Autocomplete Flight")
# async def autocomplete_city(query: str):
 #   airports = get_airports_data()

  #  Matching = [airport for airport in airports if (query.lower() in airport["city"].lower() or query.lower() in airport["name"].lower() or query.lower() in airport["country"].lower() or query.lower() in airport["code"].lower() or query.lower() in airport["countrycode"])]
   # return Matching
@app.get("/autocomplete")
async def autocomplete_city(query: str):
    airports = get_airports_data()

    Matching = [airport for airport in airports if (query.lower() in airport["city"].lower() or query.lower() in airport["name"].lower() or query.lower() in airport["country"].lower() or query.lower() in airport["code"].lower() or query.lower() in airport["countrycode"])]
    return Matching

#Search for Domestic or International Oneway
@app.get("/Oneway Search Flight")
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
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
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
    else:
        return final

#Search for Domestic or International Return
@app.get("/Return Search Flight")
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
    headers  ={
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
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
@app.get("/Multicity Search Flight")
def Search():
    global shared_response
    response = json.dumps(shared_response)
    url = "https://apitest.tripjack.com/fms/v1/air-search-all"
    headers ={
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    if shared_response:
        final = requests.request("POST", url, headers=headers, data=response)
        res = final.json()
        return res


#Review Selected Flight
@app.post("/Review Flight")
def Review(priceIds:list):
    url = "https://apitest.tripjack.com/fms/v1/review"
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"priceIds": priceIds})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
       # SSR_USD = extractSSR(res)
       # SSR_USD = INR_to_USD_SSR(SSR_USD)
      #  Total_USD = extractTotalPrice(res)
        return res,
  #  SSR_USD,
   # Total_USD


    

#Get Fare Rule of Selected Flight
@app.get("/Fare Rule Flight")
def Farerule(id:str,flowtype:str):
    url = "https://apitest.tripjack.com/fms/v1/farerule"
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"id": id,"flowType": flowtype})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res

#Get Seat Map of selected flight
@app.get("/Seat Map Flight")
def Seatmap(bookingid:str):
    url = "https://apitest.tripjack.com/fms/v1/seat"
    headers   = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"bookingId": bookingid})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
       # SEAT_USD = Seatmap_USD(res)
        return res,
    #SEAT_USD

#Create booking/Hold Itenary
@app.post("/Booking and Hold Booking")
def Booking(payload: dict):
    url = "https://apitest.tripjack.com/oms/v1/air/book"
    headers  = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        return response_data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    
#Fare Validate after Blocking
@app.get("/Fare Validate Flight")
def Validate(bookingid:str):
    url = "https://apitest.tripjack.com/oms/v1/air/fare-validate"
    headers =   {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"bookingId": bookingid})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res

#Confirm Booking after Holding
@app.get("/Confirm Book Flight")
def Confirm(bookingid:str,amount:float):
    url = "https://apitest.tripjack.com/oms/v1/air/confirm-book"
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"bookingId": bookingid,"paymentInfos": [{"amount": amount}]})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        '''response_string = json.dumps(res)
        insert_query = INSERT INTO json_responses (response) VALUES (%s)

        cursor.execute(insert_query, (response_string,))
        cnx.commit()'''
        return res
#Get Booking Details
@app.get("/Booking Details Flight")
def Bookingdetails(bookingid:str):
    url = "https://apitest.tripjack.com/oms/v1/booking-details"
    headers = {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"bookingId": bookingid})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res
#Get Booking Details with Pax Pricing
@app.get("/Booking Details with Pax Pricing Flight")
def Bookingdetails(bookingid:str):
    url = "https://apitest.tripjack.com/oms/v1/booking-details"
    headers =  {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"bookingId": bookingid,"requirePaxPricing": True})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res
#Release PNR 
@app.get("/Release PNR Flight")
def ReleasePNR(bookingid:str,pnrs:list):
    url =  "https://apitest.tripjack.com/oms/v1/air/unhold"
    headers =   {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = json.dumps({"bookingId":bookingid,"pnrs":pnrs})
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res
#Get User Balance
@app.get("/User Balance Flight")
def Userbalance(apikey:str):
    url =  "https://apitest.tripjack.com/ums/v1/user-detail" 
    headers =  {
    'apikey': '1122105735e4d1-f4ca-47aa-849d-67e6ec304a22',
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin':'*',
    'Access-Control-Allow-Headers':'Content-Type,Authorization',
    'Access-Control-Allow-Methods':'*'
    }
    payload = {}
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        res = response.json()
        return res


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


@app.get("/autocomplete_nationality Hotel")
async def autocomplete_nationality(query: str):

    nationality = get_nationality_data()

    Matching_nationality = [MN for MN in nationality if (query.lower() in MN["countryname"].lower() or query.lower() in MN["name"].lower() or query.lower() in MN["countryid"].lower() or query.lower() in MN["code"].lower() or query.lower() in MN["isocode"] or query.lower() in MN["dial_code"])]
    return Matching_nationality

@app.get("/autocomplete_city Hotel")
async def autocomplete_city(query: str):
    city = get_city_data()
    Matching_city = [MC for MC in city if MC["cityName"].lower().startswith(query.lower()) 
                     or (query.lower() in MC["countryName"].lower() 
                     or query.lower() in MC["type"].lower())]
    return Matching_city

#@app.get("/autocomplete_city Hotel")async def autocomplete_city(query: str):
    city = get_city_data()
    Matching_city = [MC for MC in city if (query.lower() in MC["countryName"].lower() or query.lower() in MC["cityName"].lower() or query.lower() in MC["type"].lower())]
    return Matching_city

#Dynamic Search Schema
#def SearchSchema():
    headers = {
    'apikey': TJ_KEY,
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

@app.get("/SearchSchema")
def SearchSchema(checkindate: str, checkoutdate: str, rooms: str, adults: str, child: str, city: str, currency: str, nationality: str):
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
    search['searchQuery']["checkinDate"] = checkindate
    search['searchQuery']["checkoutDate"] = checkoutdate
    search['searchQuery']["roomInfo"] = []
    rooms = int(rooms)
    adults = int(adults)
    child = int(child)
    ApR = (adults // rooms)
    CpR = (child // rooms)
    room = {}
    for i in range(rooms): 
        room["numberOfAdults"] = ApR
        adults -= ApR
        room["numberOfChild"] = CpR
        child -= CpR
        if room["numberOfChild"] > 0:
            room["childAge"] = []
            for i in range(room["numberOfChild"]):
                age = 5
                room["childAge"].append(age)
        search['searchQuery']["roomInfo"].append(room)
        room = {}
        

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

@app.post("/SearchID Hotel")
def SearchID(search:str):
    headers = {
    'apikey': "1122105735e4d1-f4ca-47aa-849d-67e6ec304a22",
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




@app.get("/HotelDetails Hotel")
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




@app.post("/CancellationPolicy Hotel")
def CancellationPolicy(hotelid:str,optionid:str):
    headers = {
    'apikey': "1122105735e4d1-f4ca-47aa-849d-67e6ec304a22",
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


@app.get("/Review Hotel")
def Review(hotelid:str,optionid:str):
    headers = {
    'apikey': "1122105735e4d1-f4ca-47aa-849d-67e6ec304a22",
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
@app.get("/Create Payment")
def CreateTransaction(amount:float,  currency: str):
    if currency == "BTC":
        create_transaction_params_BTC = {
            'cmd': 'create_transaction',
            'amount': amount,
            'currency1': 'INR',
            'currency2': 'BTC',
            'buyer_email': 'pietrip@gmail.com'
        }
    elif currency == "LTC":
        create_transaction_params_LTC = {
            'cmd': 'create_transaction',
            'amount': amount,
            'currency1': 'INR',
            'currency2': 'LTC',
            'buyer_email': 'pietrip@gmail.com'
        }

    elif currency == "USDT":
          create_transaction_params_USDT = {
            'cmd' : 'create_transaction',
            'amount' :  amount,
            'currency1' : "INR",
            "currency2" : "USDT",
            'buyer_email' : 'pietrip@gmail.com'
        }
    elif currency == "ETH":
         create_transaction_params_ETH = {
            'cmd' : 'create_transaction',
            'amount' :  amount,
            'currency1' : "INR",
            "currency2" : "ETH",
            'buyer_email' : 'pietrip@gmail.com'
        }

    #Client instance
    client = CryptoPayments("58652ac636c2f9b4806e30cddbf90018a0fe920d5d2dcd49f7c93839dae670f5", "3e7f08B845FbcAa815Af72e08B8955F45f15ee4Ae467af1460E8C6Da10a176ae", "")

    #make the call to createTransaction crypto payments API
    transactionBTC = client.createTransaction(create_transaction_params_BTC)
    #transactionLTC = client.createTransaction(create_transaction_params_LTC)
   # transactionUSDT = client.createTransaction(create_transaction_params_USDT)
    #transactionETH = client.createTransaction(create_transaction_params_ETH)

    #if transactionBTC['error'] == 'ok' and transactionLTC['error'] == 'ok' and transactionETH['error'] == 'ok' and transactionBNB['error'] == 'ok':  #check error status 'ok' means the API returned with desired result
    return transactionBTC

#@app.get("/Create Payment")def CreateTransaction(amount:float):

    create_transaction_params_BTC = {
            'cmd' : 'create_transaction',
            'amount' :  amount,
            'currency1' : "USD",
            "currency2" : "BTC",
            'buyer_email' : 'pietrip@gmail.com'
        }
    create_transaction_params_LTC = {
            'cmd' : 'create_transaction',
            'amount' :  amount,
            'currency1' : "USD",
            "currency2" : "LTC",
            'buyer_email' : 'pietrip@gmail.com'
        }
    create_transaction_params_USDT = {
            'cmd' : 'create_transaction',
            'amount' :  amount,
            'currency1' : "USDT",
            "currency2" : "BNB",
            'buyer_email' : 'pietrip@gmail.com'
        }
    create_transaction_params_ETH = {
            'cmd' : 'create_transaction',
            'amount' :  amount,
            'currency1' : "USD",
            "currency2" : "ETH",
            'buyer_email' : 'pietrip@gmail.com'
        }

    #Client instance
    client = CryptoPayments(API_KEY, API_SECRET, IPN_URL)

    #make the call to createTransaction crypto payments API
    transactionBTC = client.createTransaction(create_transaction_params_BTC)
    transactionLTC = client.createTransaction(create_transaction_params_LTC)
    transactionUSDT = client.createTransaction(create_transaction_params_USDT)
    transactionETH = client.createTransaction(create_transaction_params_ETH)

    #if transactionBTC['error'] == 'ok' and transactionLTC['error'] == 'ok' and transactionETH['error'] == 'ok' and transactionBNB['error'] == 'ok':  #check error status 'ok' means the API returned with desired result
    return transactionBTC,transactionLTC,transactionETH,transactionUSDT
