import requests
import datetime
import os
import pyfiglet

def print_header():
    """Print the WALLETRAX banner using ASCII art"""
    banner = pyfiglet.figlet_format("WALLETRAX")
    print(banner)
    
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
WALLET_FILE = "walletrax.txt"
TOKEN_IDS_FILE = "tokenIDs.txt"
TOKEN_MAP = None  # Global cache for the official token list

def get_token_list():
    """Fetch and cache the official token list mapping mint addresses to token metadata."""
    global TOKEN_MAP
    if TOKEN_MAP is None:
        token_list_url = "https://raw.githubusercontent.com/solana-labs/token-list/main/src/tokens/solana.tokenlist.json"
        try:
            response = requests.get(token_list_url)
            data = response.json()
            tokens = data.get('tokens', [])
            # Create a dictionary mapping mint addresses to token metadata
            TOKEN_MAP = {token['address']: token for token in tokens}
        except Exception as e:
            print("Error fetching token list:", e)
            TOKEN_MAP = {}
    return TOKEN_MAP

def load_custom_tokens():
    """Load custom token mappings from tokenIDs.txt.
       Each line should be formatted as: token_address,ticker
    """
    custom_tokens = {}
    if os.path.exists(TOKEN_IDS_FILE):
        with open(TOKEN_IDS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(",")
                    if len(parts) == 2:
                        token_address = parts[0].strip()
                        ticker = parts[1].strip()
                        custom_tokens[token_address] = ticker
    return custom_tokens

def save_custom_token_mapping(token_address, ticker):
    """Save a new token mapping to tokenIDs.txt if it doesn't already exist."""
    custom_tokens = load_custom_tokens()
    if token_address in custom_tokens:
        print("This token address is already mapped to:", custom_tokens[token_address])
        return
    with open(TOKEN_IDS_FILE, "a") as f:
        f.write(f"{token_address},{ticker}\n")
    print("Token mapping added.")

def add_custom_token_mapping():
    """Prompt the user to add a custom token mapping."""
    token_address = input("Enter token mint address: ").strip()
    ticker = input("Enter token ticker/ID: ").strip()
    if token_address and ticker:
        save_custom_token_mapping(token_address, ticker)
    else:
        print("Invalid input. Both token address and ticker are required.")

def get_wallet_balances(wallet_address):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet_address, 
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ]
    }
    response = requests.post(SOLANA_RPC_URL, json=payload).json()
    official_tokens = get_token_list()  # Official token metadata
    custom_tokens = load_custom_tokens()  # Custom mappings from tokenIDs.txt
    
    if 'result' in response and 'value' in response['result']:
        balances = []
        for account in response['result']['value']:
            token_info = account['account']['data']['parsed']['info']
            mint = token_info['mint']
            amount = int(token_info['tokenAmount']['amount']) / (10 ** int(token_info['tokenAmount']['decimals']))
            # Use official token list first, then custom tokens, fallback to mint address
            if mint in official_tokens:
                symbol = official_tokens[mint].get("symbol", mint)
            elif mint in custom_tokens:
                symbol = custom_tokens[mint]
            else:
                symbol = mint
            balances.append((symbol, amount))
        
        balances.sort(key=lambda x: x[1], reverse=True)
        return balances[:5]
    
    return []

def get_wallet_transactions(wallet_address):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [wallet_address, {"limit": 10}]
    }
    response = requests.post(SOLANA_RPC_URL, json=payload).json()
    
    if 'result' in response:
        transactions = []
        for tx in response['result']:
            transactions.append({
                "signature": tx['signature'],
                "slot": tx['slot'],
                "blockTime": datetime.datetime.utcfromtimestamp(tx['blockTime']).strftime('%Y-%m-%d %H:%M:%S') 
                             if 'blockTime' in tx and tx['blockTime'] is not None else "Unknown"
            })
        return transactions
    
    return []

def get_first_transaction_date(wallet_address):
    # Paginate through the wallet's transaction history until we reach the oldest transaction.
    limit = 100
    before = None
    oldest_tx = None

    while True:
        params = {"limit": limit}
        if before:
            params["before"] = before

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet_address, params]
        }
        response = requests.post(SOLANA_RPC_URL, json=payload).json()
        if 'result' not in response or not response['result']:
            break

        oldest_tx = response['result'][-1]
        if len(response['result']) < limit:
            break

        before = oldest_tx['signature']

    if oldest_tx and 'blockTime' in oldest_tx and oldest_tx['blockTime'] is not None:
        return datetime.datetime.utcfromtimestamp(oldest_tx['blockTime']).strftime('%Y-%m-%d')
    return "Unknown"

def load_wallets():
    wallets = []
    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, "r") as f:
            wallets = [line.strip() for line in f if line.strip()]
    return wallets

def save_wallet(wallet_address):
    wallets = load_wallets()
    if wallet_address not in wallets:
        with open(WALLET_FILE, "a") as f:
            f.write(wallet_address + "\n")

def select_wallet():
    wallets = load_wallets()
    if wallets:
        print("Saved Wallets:")
        for idx, wallet in enumerate(wallets, 1):
            print(f"{idx}. {wallet}")
        print(f"{len(wallets)+1}. Add a new wallet")
        
        try:
            choice = int(input("Select an option: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            return select_wallet()
        
        if 1 <= choice <= len(wallets):
            return wallets[choice - 1]
        elif choice == len(wallets) + 1:
            return add_wallet()
        else:
            print("Invalid option. Try again.")
            return select_wallet()
    else:
        print("No saved wallets found. Please add a new wallet.")
        return add_wallet()

def add_wallet():
    wallet_address = input("Enter new Solana wallet address: ").strip()
    if wallet_address:
        save_wallet(wallet_address)
        return wallet_address
    else:
        print("Invalid wallet address.")
        return add_wallet()

def track_wallet():
    wallet_address = select_wallet()
    
    print("\nFetching data...\n")
    
    balances = get_wallet_balances(wallet_address)
    transactions = get_wallet_transactions(wallet_address)
    first_tx_date = get_first_transaction_date(wallet_address)
    
    print("Top 5 Balances:")
    for symbol, amount in balances:
        print(f"Token: {symbol} - Balance: {amount}")
    
    print("\nLast 10 Transactions:")
    for tx in transactions:
        print(f"Signature: {tx['signature']}, Slot: {tx['slot']}, Time: {tx['blockTime']}")
    
    print(f"\nFirst Transaction Date: {first_tx_date}\n")

def main():
    while True:
        print_header()  # Display the ASCII art header at the beginning of each menu iteration
        
        print("Main Menu:")
        print("1. Track Wallet")
        print("2. Add Custom Token Mapping")
        print("3. Quit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            track_wallet()
        elif choice == "2":
            add_custom_token_mapping()
        elif choice == "3":
            print("Exiting.")
            break
        else:
            print("Invalid option. Please try again.\n")

if __name__ == "__main__":
    main()
