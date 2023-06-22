import requests
import time

def get_blacklisted_ips(API_url):
    now = int(time.time())
    five_minutes_ago = now - 3600
    five_minutes_ago = str(five_minutes_ago)
    API_response = requests.get(API_url + five_minutes_ago)
    data = API_response.text
    return data

print(get_blacklisted_ips('https://api.blocklist.de/getlast.php?time='))

