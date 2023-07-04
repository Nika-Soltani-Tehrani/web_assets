import datetime

def toDateTime(dateString): 
    return datetime.datetime.strptime(dateString, "%Y-%m-%d")


def countRequests(requestsList):
    return len(requestsList)


def countSuccessRequests(requestsList):
    count = 0
    for request in requestsList:
        if request['result'] >= 200 and request['result'] <= 299:
            count += 1
    return count

def countFailiureRequests(requestsList):
    count = 0
    for request in requestsList:
        if request['result'] < 200 or request['result'] > 299:
            count += 1
    return count
