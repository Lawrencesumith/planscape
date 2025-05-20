import requests

url = "https://api.makcorps.com/hotel"  # Use the correct endpoint from their docs

headers = {
    "Authorization": "680a74783fabd1472d159d6f",  # Replace with your actual API key
    "Content-Type": "application/json"
}

payload = {
    "city": "Coimbatore",   # You can test with any city
    "checkin_date": "2025-05-01",
    "checkout_date": "2025-05-03"
}

response = requests.post(url, headers=headers, json=payload)

print(response.status_code)
print(response.json())
