import requests
import logging
from datetime import datetime, timedelta
import pytz
from hashlib import sha256
import time


class Session:
    def __init__(self, id, name, address, district, pay, date, numSlots):
        self.id = id
        self.name = name
        self.address = address
        self.district = district
        self.pay = pay
        self.date = date
        self.numSlots = numSlots

    def __str__(self):
        return "NAME : " + self.name + \
               ", ADDRESS : " + self.address + \
               ", DISTRICT : " + self.district + \
               ", PAY : " + self.pay + \
               ", DATE : " + self.date + \
               ", SLOTS : " + str(self.numSlots)



class Telegram:
    chatId = ""  # chatId of the telegram group
    token = ""   # token of the bot

    def sendMessage(self,msg):
        sendText = 'https://api.telegram.org/bot' + self.token + '/sendMessage?chat_id=' + self.chatId + '&parse_mode=Markdown&text=' + msg
        response = requests.get(sendText)

        if response.status_code != 200:
            print("Sending to telegram failed!")


class CowinApp:
    # Server end points
    PROD_SERVER = "https://cdn-api.co-vin.in/api"
    TEST_SERVER = "https://api.demo.co-vin.in/api"

    STANDARD_HEADERS = {"Accept": "application/json",
                        "Connection": "keep-alive",
                        "User-Agent": "CowinApp/0.0.1",
                        }

    # Utility end points
    GET_STATES = "/v2/admin/location/states"
    GET_DISTRICT = "/v2/admin/location/districts/"  # {state_id}
    GET_CALENDAR = "/v2/appointment/sessions/public/calendarByDistrict"
    POST_GENOTP = "/v2/auth/public/generateOTP"
    POST_CONFIRMOTP = "/v2/auth/public/confirmOTP"


    def __init__(self):
        now = datetime.now(tz=pytz.timezone('Asia/Kolkata'))
        fname = now.strftime("%H_%M_%S") + ".log"

        logging.basicConfig(filename=fname, filemode='w',
                            format='%(asctime)s - %(message)s',
                            level=logging.INFO)

        self.txn_id = ""
        self.token = ""

    def getStatesOfInterest(self, locationOfInterest):
        statesOfInterest = locationOfInterest.keys()
        stateIds = {}

        urlToHit = self.PROD_SERVER + self.GET_STATES
        logging.info("Querying for all available states at " + urlToHit)

        r = requests.get(url=urlToHit, headers=self.STANDARD_HEADERS)

        if r.status_code == 200:
            stateData = r.json()
            for state in stateData["states"]:
                if state["state_name"] in statesOfInterest:
                    logging.info("State id for " + state["state_name"] + " is " + str(state["state_id"]))
                    stateIds[state["state_name"]] = state["state_id"]

        else:
            logging.fatal(r.content)
            logging.fatal("Couldn't retrieve states")

        return stateIds

    def getDistrictsOfInterest(self, locationOfInterest):
        stateIds = self.getStatesOfInterest(locationOfInterest)
        districtIds = {}
        if len(stateIds) == 0:
            logging.error("No states to search")
        else:
            for state in locationOfInterest:
                if state not in stateIds:
                    logging.error("Couldn't find state id for " + state)
                    continue

                urlToHit = self.PROD_SERVER + self.GET_DISTRICT + str(stateIds[state])

                logging.info("Getting districts for state " + state)
                r = requests.get(url=urlToHit, headers=self.STANDARD_HEADERS)

                if r.status_code == 200:
                    districtData = r.json()

                    for districts in districtData["districts"]:
                        if districts["district_name"] in locationOfInterest[state]:
                            districtIds[districts["district_name"]] = districts["district_id"]

                else:
                    logging.fatal(r.content)
                    logging.fatal("Couldn't retrieve districts for " + state)

        return districtIds

    def getAvailableSessions(self, districtIds, sessionChecker):
        sessions = []

        for district in districtIds:
            tomorrow = datetime.today() #+ timedelta(days=1)
            dateStr = tomorrow.strftime("%d-%m-%Y")

            logging.info("Fetching 7 day calendar for " + district + " starting " + dateStr)

            urlToHit = self.PROD_SERVER + self.GET_CALENDAR
            params = {
                "district_id": districtIds[district],
                "date": dateStr,
            }

            time.sleep(4)
            r = requests.get(url=urlToHit, params=params, headers=self.STANDARD_HEADERS)

            if r.status_code == 200:
                calendarData = r.json()
                for center in calendarData["centers"]:
                    for session in center["sessions"]:
                        if sessionChecker(session) and session["available_capacity"] > 0:
                            s = Session(session["session_id"], center["name"], center["address"],
                                        center["district_name"], center["fee_type"], session["date"],
                                        session["available_capacity"])

                            sessions.append(s)
                            logging.info("FOUND a session " + str(session))

            else:
                self.prevSessionsSent = []
                logging.fatal("Unable to get calendar for " + district)
                logging.fatal(r.content)

        return sessions

    def authenticate(self):
        urlToHit = self.PROD_SERVER + self.POST_GENOTP

        print("Enter mobile number : ")
        phoneNumber = input().strip()

        params = {
            "mobile": str(phoneNumber)
        }

        r = requests.post(url=urlToHit, json=params, headers=self.STANDARD_HEADERS)

        if r.status_code == 200:
            genOTPData = r.json()
            self.txn_id = genOTPData["txnId"]
            logging.info("Received the transaction id " + self.txn_id)

            urlToHit = self.PROD_SERVER + self.POST_CONFIRMOTP
            print("Enter the OTP received : ")
            otp = input().strip()
            hashOTP = sha256(otp.encode('utf-8')).hexdigest()

            params = {
                "otp": hashOTP,
                "txnId": self.txn_id
            }

            r = requests.post(url=urlToHit, json=params, headers=self.STANDARD_HEADERS)

            if r.status_code == 200:
                tokenData = r.json()
                self.token = tokenData["token"]
                logging.info("Received the token " + self.token)
                print("Authentication successful!")

                return True
            else:
                print("Something went bad" + str(r.content))

        else:
            print("Something went wrong!" + str(r.content))

        return False

    def book(self, sessions):
        # This is not open to all :(
        pass
