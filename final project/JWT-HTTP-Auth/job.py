import threading
import time
import requests
from init import sleeping_time


HOST = 'http://127.0.0.1:5000'


def run():

    payload = {'username': 'mary', 'password': '123456789'}
    headers = {}
    response = requests.request("POST", HOST + "/api/login", headers=headers, data=payload)
    token = response.json()['token']

    headers = {'Authorization': token}
    response = requests.request("GET", HOST + "/api/get_urls", headers=headers)
    urls = response.json()['urls']

    for url in urls:
        address = url['address']
        response = requests.request("GET", address)
        status_code = response.status_code
        payload = {'result': status_code, 'url_id': url['id']}
        headers = {'Authorization': token}
        response = requests.request("POST", HOST + "/api/add_request", headers=headers, data=payload)


while True:
    threading.Thread(target=run).start()
    time.sleep(sleeping_time)

