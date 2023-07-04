import time
import requests
import datetime
import schedule

# Config
USERNAME = 'admin'
PASS = 123456
HOST = 'http://127.0.0.1:5000'


def check():

    print("start ---- ", datetime.datetime.now())

    # login
    payload={'username': 'admin','password': '123456'}
    headers = {}
    response = requests.request("POST", HOST+"/v1/users/login", headers=headers, data=payload)
    token = response.json()['token']

    # getting all urls
    headers = {'Authorization':token}
    response = requests.request("GET", HOST+"/v1/urls/all", headers=headers)
    urls = response.json()['urls']

    # comparing last_checking_date with now() to see if it is greater than checking_seconds
    for url in urls:
        last_checking_date = datetime.datetime.strptime(url['last_checking_date'], '%Y-%m-%dT%H:%M:%S')
        checking_seconds = url['checking_seconds']

        print(datetime.datetime.now(), " >>>>>>>> URLS Loop >>>>>>>> ", "last checking date is ", last_checking_date, "for ", url['address'])
        
        if (datetime.datetime.now()-last_checking_date).total_seconds() >= checking_seconds:
            pass
            # do check
            address = url['address']
            response = requests.request("GET", address)
            status_code = response.status_code

            # updaing last_checking_date
            payload={'url_id': url['id']}
            headers = {'Authorization':token}
            response = requests.request("POST", HOST+"/v1/urls/checked", headers=headers, data=payload)

            # insert the result into requests database
            payload={'result': status_code,'url_id': url['id']}
            headers = {'Authorization':token}
            response = requests.request("POST", HOST+"/v1/requests/add", headers=headers, data=payload)

            print(datetime.datetime.now(), " >>>>>>>> UPDATED >>>>>>>> ", "address is ", address, checking_seconds, last_checking_date, status_code)

    print("end ---- ", datetime.datetime.now())


def test():
    print("start ---- ", datetime.datetime.now())

    # login
    payload={'username': 'admin','password': '123456'}
    headers = {}
    response = requests.request("POST", HOST+"/v1/users/login", headers=headers, data=payload)
    token = response.json()['token']

    print("end ---- ", datetime.datetime.now())

schedule.every(30).seconds.do(check)

while True:
	schedule.run_pending()
    # time.sleep(1)