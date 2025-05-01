from flask import Flask, request, jsonify
import os, requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DSN = os.getenv("UNIPILE_DSN")  # e.g. "yourteam.unipile.com"
API_KEY = os.getenv("UNIPILE_API_KEY")
ACCOUNT_ID = os.getenv("UNIPILE_ACCOUNT_ID") # optional, can be set in the request
BASE_URL = f"https://{DSN}/api/v1"


@app.route('/get_recipient_id', methods=['GET'])
def get_recipient_id():
    # Extract query parameters
    public_id = request.args.get('public_identifier')
    account_id = request.args.get('account_id') or ACCOUNT_ID

    if not public_id:
        return jsonify({"error": "Missing 'public_identifier' query parameter"}), 400

    # Prepare request to Unipile
    url = f"{BASE_URL}/users/{public_id}"
    headers = {
        "X-API-KEY": API_KEY,
        "accept": "application/json"
    }
    params = {}
    if account_id:
        params["account_id"] = account_id  # Ensure correct account context

    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        # Extract the provider_id as recipient_id
        provider_id = data.get("provider_id")
        if not provider_id:
            return jsonify({"error": "Unexpected response format", "data": data}), 502

        return jsonify({"recipient_id": provider_id}), 200

    except requests.exceptions.HTTPError as http_err:
        # Forward error status and details
        print(f"HTTP error occurred: {http_err}")
        detail = resp.text
        return jsonify({"error": "Unipile API HTTP error", "details": detail}), resp.status_code

    except Exception as e:
        # Catch-all for other errors
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/register_linkedin_account', methods=['POST'])
def register_linkedin_account():
    """
    Endpoint to register a new LinkedIn account with Unipile.
    Expects JSON payload:
    {
        "username": "linkedin_email@example.com",
        "password": "your_linkedin_password"
    }
    """
    if not API_KEY:
        return jsonify({"error": "API key not set"}), 500

    payload = request.get_json() or {}
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        return jsonify({"error": "Missing 'username' or 'password' in request body"}), 400

    # Prepare request for Unipile API
    url = f"{BASE_URL}/accounts"
    headers = {
        "X-API-KEY": API_KEY,
        "accept": "application/json",
        "content-type": "application/json"
    }
    unipile_payload = {
        "provider": "LINKEDIN",
        "username": username,
        "password": password
    }

    try:
        resp = requests.post(url, headers=headers, json=unipile_payload)
        resp.raise_for_status() # Raise exception for 4xx/5xx errors
        # Return the successful response from Unipile
        return jsonify(resp.json()), resp.status_code

    except requests.exceptions.HTTPError as http_err:
        # Forward error status and details from Unipile
        print(f"Unipile API HTTP error occurred: {http_err}")
        try:
            detail = resp.json() # Try to parse JSON error response
        except ValueError:
            detail = resp.text # Fallback to raw text
        return jsonify({"error": "Unipile API HTTP error", "details": detail}), resp.status_code

    except requests.exceptions.RequestException as req_err:
        # Handle connection errors, timeouts, etc.
        print(f"Error communicating with Unipile API: {req_err}")
        return jsonify({"error": "Failed to communicate with Unipile API", "details": str(req_err)}), 502

    except Exception as e:
        # Catch-all for other unexpected errors
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred", "details": str(e)}), 500


@app.route('/send_linkedin_message', methods=['POST'])
def send_linkedin_message():
    if not API_KEY:
        return jsonify({"error": "API key not set"}), 500

    payload = request.get_json() or {}
    recipient_id = payload.get("recipient_id")
    message_text = payload.get("message")
    chat_id = payload.get("chat_id")  # optional

    if not recipient_id or not message_text:
        return jsonify({"error": "Missing recipient_id or message"}), 400

    # Choose endpoint
    if chat_id:
        url = f"{BASE_URL}/chats/{chat_id}/messages"
    else:
        url = f"{BASE_URL}/chats"
    
    headers = {
        "X-API-KEY": API_KEY,
        "accept": "application/json"
    }
    # Prepare form data
    data = {
        "text": message_text
    }
    if chat_id is None:
        data["account_id"] = os.getenv("UNIPILE_ACCOUNT_ID")
        data["attendees_ids"] = recipient_id

    try:
        resp = requests.post(url, headers=headers, data=data)
        resp.raise_for_status()
        return jsonify(resp.json()), 200
    except requests.RequestException as e:
        details = e.response.json() if e.response is not None else str(e)
        return jsonify({"error": "Unipile API error", "details": details}), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)