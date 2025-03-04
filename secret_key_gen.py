import base58
import json

def phantom_private_key_to_json_array(phantom_private_key: str):
    # Decode the base58-encoded private key
    private_key_bytes = base58.b58decode(phantom_private_key)
    
    # Ensure the decoded key is 64 bytes
    if len(private_key_bytes) != 64:
        raise ValueError("Invalid private key length. Expected 64 bytes.")
    
    # Convert the byte array to a list of integers
    key_list = list(private_key_bytes)
    
    # Convert the list to a JSON-formatted string
    json_array = json.dumps(key_list)
    
    return json_array

def main():
    # Prompt the user for the Phantom private key
    phantom_private_key = input("Enter your Phantom private key: ").strip()
    
    try:
        # Convert to JSON array
        json_array = phantom_private_key_to_json_array(phantom_private_key)
        print("64-byte JSON Array:")
        print(json_array)
    except ValueError as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
