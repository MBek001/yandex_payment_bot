import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()

clid = os.getenv("PARK4_CLID")
park_id = os.getenv("PARK4_PARK_ID")
api_key = os.getenv("PARK4_API_KEY")

categories_url = "https://fleet-api.taxi.yandex.net/v2/parks/transactions/categories/list"

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'X-Park-ID': park_id,
    'X-Client-ID': clid,
    'X-API-Key': api_key
}

print("=" * 80)
print("TESTING DIFFERENT REQUEST FORMATS")
print("=" * 80)

# Attempt 1: park_id in request body
print("\n📝 Attempt 1: park_id in request body (POST)")
try:
    response = requests.post(
        categories_url,
        headers=headers,
        json={"park_id": park_id},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ SUCCESS!")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Attempt 2: park.id in request body (nested)
print("\n📝 Attempt 2: park.id in nested format (POST)")
try:
    response = requests.post(
        categories_url,
        headers=headers,
        json={"park": {"id": park_id}},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ SUCCESS!")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Attempt 3: query parameter with different key
print("\n📝 Attempt 3: Using 'park.id' as query param")
try:
    response = requests.post(
        categories_url,
        headers=headers,
        params={"park.id": park_id},
        json={},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ SUCCESS!")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Attempt 4: With query nested in body
print("\n📝 Attempt 4: query.park.id in body")
try:
    response = requests.post(
        categories_url,
        headers=headers,
        json={"query": {"park": {"id": park_id}}},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ SUCCESS!")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Attempt 5: GET with query parameters
print("\n📝 Attempt 5: GET with park_id query param")
try:
    response = requests.get(
        categories_url,
        headers=headers,
        params={"park_id": park_id},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ SUCCESS!")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Attempt 6: GET with park.id query param
print("\n📝 Attempt 6: GET with 'park.id' query param")
try:
    response = requests.get(
        categories_url,
        headers=headers,
        params={"park.id": park_id},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ SUCCESS!")
        categories_data = response.json()
        print(json.dumps(categories_data, indent=2, ensure_ascii=False))

        # Save to file
        with open('yandex_categories.json', 'w', encoding='utf-8') as f:
            json.dump(categories_data, f, indent=2, ensure_ascii=False)
        print("\n💾 Saved to: yandex_categories.json")

        # Display formatted
        print("\n" + "=" * 80)
        print("CATEGORIES:")
        print("=" * 80)
        if isinstance(categories_data, dict) and 'categories' in categories_data:
            for idx, cat in enumerate(categories_data['categories'], 1):
                print(f"{idx}. {cat.get('id', cat.get('category_id'))}: {cat.get('name', 'N/A')}")

    else:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)