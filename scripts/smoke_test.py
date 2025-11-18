import sys
import time
import requests

BASE = "http://127.0.0.1:8000"


def get(path):
    url = BASE + path
    try:
        r = requests.get(url, timeout=5)
        print(f"GET {path} -> {r.status_code}")
        print(r.text[:1000])
    except Exception as e:
        print(f"GET {path} -> ERROR: {e}")


def post(path, data):
    url = BASE + path
    try:
        r = requests.post(url, json=data, timeout=8)
        print(f"POST {path} -> {r.status_code}")
        print(r.text[:1000])
    except Exception as e:
        print(f"POST {path} -> ERROR: {e}")


def main():
    print("Waiting a moment for server to be ready...")
    time.sleep(1)
    get('/api/dev/version/')
    get('/api/market/snapshot/')
    post('/api/parse/', {'text': 'hello'})


if __name__ == '__main__':
    main()
