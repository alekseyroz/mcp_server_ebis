import requests
from base64 import b64encode


BASE_URL = "https://ia.ebis5.com/api/integration/external"
USERNAME = "IslanderAvApiAccess"
PASSWORD = "A0606045-CB8F-46F6-A6BE-355A73455541"


def get_auth_header() -> dict:
    token = b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def get(endpoint: str, params: dict = None) -> dict:
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers=get_auth_header(),
        params=params,
    )
    response.raise_for_status()
    return response.json()


def post(endpoint: str, body: dict) -> dict:
    response = requests.post(
        f"{BASE_URL}/{endpoint}",
        headers={**get_auth_header(), "Content-Type": "application/json"},
        json=body,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------

def create_workorder():
    print("\n=== Create Work Order ===")

    tail = input("Aircraft tail number (RegNum): ").strip()
    if not tail:
        print("Tail number is required.")
        return

    # Collect work order items
    items = []
    print("\nAdd line items (press Enter with no input to finish):")
    line = 1
    while True:
        discrepancy = input(f"  Item {line} - Discrepancy (or Enter to finish): ").strip()
        if not discrepancy:
            break
        notes = input(f"  Item {line} - Notes (optional): ").strip()
        item = {"LineNumber": line, "Discrepancy": discrepancy}
        if notes:
            item["Notes"] = notes
        items.append(item)
        line += 1

    payload = {
        "RegNum": tail,
        "DefaultToAircraftCity": True,
        "DefaultToAircraftPrimaryCustomer": True,
        "UseAnyBillingProfile": True,
    }
    if items:
        payload["Items"] = items

    print(f"\nSubmitting work order for {tail}...")
    result = post("workorder/addupdate", payload)
    data = result.get("Data", {})

    msg = data.get("MessageID", "")
    if msg == "OK":
        print(f"\n  Work Order ID : {data.get('ID')}")
        print(f"  Customer      : {data.get('CustomerName')}")
        print(f"  City          : {data.get('CityAbbr')}")
        print(f"  Link          : {data.get('EBisWoLink')}")
        if data.get("ItemResult"):
            print(f"  Items created : {len(data['ItemResult'])}")
            for item in data["ItemResult"]:
                print(f"    [{item.get('ID')}] {item.get('Discrepancy')}")
    else:
        print(f"\n  Error: {data.get('MessageText') or data.get('MessageID')}")
        validation = data.get("ValidationErrors")
        if validation:
            for field, errors in validation.items():
                print(f"    {field}: {', '.join(errors)}")


if __name__ == "__main__":
    create_workorder()
