import requests
import time

start = time.time()
res = requests.post(
    "http://127.0.0.1:8000/api/jd_match",
    json={"jd": "Need a React developer", "roles": ["Frontend"], "location": "India"}
)
end = time.time()

print("Time taken:", round(end - start, 2), "seconds")
print("Response:", res.status_code)
if res.status_code == 200:
    print(len(res.json().get("candidates", [])), "candidates returned from JD Match!")
else:
    print(res.text)
