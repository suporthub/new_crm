import requests
import json

# Base URL for the API
base_url = "http://localhost:8000/api/allotleadmanager/"

# Test cases with different countries
test_cases = [
    {
        "name": "US Lead",
        "data": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "1234567890",
            "address": "123 Main St, New York, United States",
            "country": "US"
        }
    },
    {
        "name": "India Lead",
        "data": {
            "first_name": "Raj",
            "last_name": "Patel",
            "email": "raj.patel@example.com",
            "phone": "9876543210",
            "address": "456 Park Avenue, Mumbai, India",
            "country": "IN"
        }
    },
    {
        "name": "UK Lead",
        "data": {
            "first_name": "Emma",
            "last_name": "Watson",
            "email": "emma.watson@example.com",
            "phone": "4567891230",
            "address": "789 Oxford St, London, United Kingdom",
            "country": "GB"
        }
    },
    {
        "name": "Lead without country but with address",
        "data": {
            "first_name": "David",
            "last_name": "Smith",
            "email": "david.smith@example.com",
            "phone": "7891234560",
            "address": "101 Queen Street, Toronto, Canada",
            # No country provided, should extract from address
        }
    }
]

# Run the tests
for test in test_cases:
    print(f"\nTesting: {test['name']}")
    try:
        response = requests.post(base_url, json=test['data'])
        print(f"Status Code: {response.status_code}")
        if response.status_code == 201:
            lead_data = response.json()
            print(f"Lead created with ID: {lead_data.get('id')}")
            print(f"Assigned manager: {lead_data.get('manager_username')}")
            print(f"Expected country: {test['data'].get('country', 'Should extract from address')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
