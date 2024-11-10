import random
import time
import webbrowser
from typing import Any, Dict, List, Optional

from algosdk import account, mnemonic, transaction
from algosdk.transaction import AssetTransferTxn, SignedTransaction
from algosdk.v2client import algod


class Account:

    algod_address = "https://testnet-api.algonode.cloud"
    algod_client = algod.AlgodClient("", algod_address)
    algo_conversion = 0.000001

    def __init__(
        self,
        address: str,
        private_key: Optional[str] = None,
        mnemonic_phrase: Optional[str] = None,
    ) -> None:
        self.address = address
        self.private_key = private_key
        self.mnemonic_phrase = mnemonic_phrase

    def account_info(self) -> Dict[str, Any]:
        try:
            return self.algod_client.account_info(self.address)
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return {}

    def check_balance(self) -> int:
        account_info = self.account_info()
        return account_info["amount"] * self.algo_conversion

    def fund_address(self) -> None:

        if self.check_balance() <= 1:
            print(
                f"The address {self.address} has not been funded and will not be able to transact with other accounts."
            )
            print(
                f"Please fund address {self.address} using the algorand test dispensor."
            )
            try:
                webbrowser.open_new_tab("https://bank.testnet.algorand.network/")
            except webbrowser.Error:
                print(
                    "Failed to open URL in browser. Please manually open the URL provided."
                )
                print("URL:", "https://bank.testnet.algorand.network/")

            while self.check_balance() <= 1:
                print(f"Waiting for address {self.address} to be funded...")
                time.sleep(5)

            print(
                f"Address {self.address} has been funded and has {self.check_balance()} algoes!"
            )
        else:
            print(
                f"Address {self.address} has been funded and has {self.check_balance()} algoes!"
            )


# Utility Functions
###############################################################################################################################
def process_atomic_transactions(
    self, transactions: List[AssetTransferTxn], accounts: List[Account]
) -> List[SignedTransaction]:
    signed_txns = []
    gid = transaction.calculate_group_id(transactions)
    for txn in transactions:
        txn.group = gid

    for txn, account in zip(transactions, accounts):
        signed_txn = txn.sign(account.private_key)
        signed_txns.append(signed_txn)

    return signed_txns


# Create UCTZAR Asset
def create_uctzar_asset(manager_address: Account):
    # Parameters for ASA creation - fixed for this example
    params = manager_address.algod_client.suggested_params()
    txn = transaction.AssetConfigTxn(
        sender=manager_address.address,
        sp=params,
        total=1_000_000,  # Total supply of UCTZAR
        default_frozen=False,
        unit_name="UCTZAR",
        asset_name="South African Rand Stablecoin",
        manager=manager_address.address,
        reserve=manager_address.address,
        freeze=manager_address.address,
        clawback=manager_address.address,
        decimals=2,
    )
    signed_txn = txn.sign(manager_address.private_key)
    txid = manager_address.algod_client.send_transaction(signed_txn)
    print("Creating UCTZAR asset, TXID:", txid)
    return txid
