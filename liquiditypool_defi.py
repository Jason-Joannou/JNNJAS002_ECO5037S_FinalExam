import random
import time
import webbrowser
from typing import Any, Dict, List, Optional

from algosdk import account, mnemonic, transaction
from algosdk.transaction import AssetTransferTxn, PaymentTxn, SignedTransaction
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


class LiquidityPool:

    def __init__(self, pool_account: Account, asset_id: int):
        self.pool_ALGO = 0
        self.pool_UCTZAR = 0
        self.total_lp_tokens = 0
        self.lp_tokens = {}
        self.pool_account = pool_account
        self.asset_id = asset_id

    def add_liquidity(
        self, provider: Account, amount_algo: float, amount_uctzar: float
    ):
        converted_ammount = int(amount_algo / Account.algo_conversion)
        txn_1 = PaymentTxn(
            sender=provider.address,
            receiver=self.pool_account.address,
            amt=converted_ammount,  # Convert ALGO to microAlgos
            sp=self.pool_account.algod_client.suggested_params(),
        )

        txn_2 = AssetTransferTxn(
            sender=provider.address,
            receiver=self.pool_account.address,
            amt=int(
                amount_uctzar * 1e2
            ),  # Convert UCTZAR to smallest unit (2 decimals)
            index=self.asset_id,
            sp=self.pool_account.algod_client.suggested_params(),
        )

        liquidity_txns = [txn_1, txn_2]
        signed_txns = process_atomic_transactions(
            transactions=liquidity_txns, account=provider
        )

        txid = self.pool_account.algod_client.send_transactions(signed_txns)
        _ = transaction.wait_for_confirmation(self.pool_account.algod_client, txid)

        # Update pool balances and LP tokens
        self.pool_ALGO += amount_algo
        self.pool_UCTZAR += amount_uctzar
        lp_token_amount = amount_algo + amount_uctzar
        self.total_lp_tokens += lp_token_amount
        self.lp_tokens[provider.address] = (
            self.lp_tokens.get(provider.address, 0) + lp_token_amount
        )
        print(f"LP Tokens for {provider.address}: {self.lp_tokens[provider.address]}")

    def trade_algo_uctzar(self, trader: Account, amount_algo: float):

        # Trade fee calculation
        trade_fee = amount_algo * 0.003  # 0.3% fee
        net_amount_algo = amount_algo - trade_fee
        amount_uctzar = net_amount_algo * 2

        net_converted_amount = int(net_amount_algo / Account.algo_conversion)

        txn_1 = PaymentTxn(
            sender=trader.address,
            receiver=self.pool_account.address,
            amt=net_converted_amount,  # Convert ALGO to microAlgos
            sp=self.pool_account.algod_client.suggested_params(),
        )

        txn_2 = AssetTransferTxn(
            sender=self.pool_account.address,
            receiver=trader.address,
            amt=int(
                amount_uctzar * 1e2
            ),  # Convert UCTZAR to its smallest unit (2 decimals)
            index=self.asset_id,
            sp=self.pool_account.algod_client.suggested_params(),
        )

        signed_txns = process_atomic_transactions(
            transactions=[txn_1, txn_2], account=trader
        )

        txid = self.pool_account.algod_client.send_transactions(signed_txns)
        _ = transaction.wait_for_confirmation(self.pool_account.algod_client, txid)

        # Update pool balances and LP tokens
        self.pool_ALGO += net_amount_algo
        self.pool_UCTZAR -= amount_uctzar
        lp_token_amount = net_amount_algo + amount_uctzar
        self.total_lp_tokens += lp_token_amount
        self.lp_tokens[trader.address] = (
            self.lp_tokens.get(trader.address, 0) + lp_token_amount
        )
        print(f"LP Tokens for {trader.address}: {self.lp_tokens[trader.address]}")
        print(f"{trader.address} traded {amount_algo} ALGO for {amount_uctzar} UCTZAR.")
        print(f"Trade fee of {trade_fee} ALGO added to the pool.")


# Utility Functions
###############################################################################################################################
def process_atomic_transactions(
    transactions: List[AssetTransferTxn], account: Account
) -> List[SignedTransaction]:
    signed_txns = []
    gid = transaction.calculate_group_id(transactions)
    for txn in transactions:
        txn.group = gid
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
