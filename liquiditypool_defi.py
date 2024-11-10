import random
import time
import webbrowser
from typing import Any, Dict, List, Optional

from algosdk import account, mnemonic, transaction
from algosdk.transaction import (
    AssetOptInTxn,
    AssetTransferTxn,
    PaymentTxn,
    SignedTransaction,
)
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

    def __init__(self, pool_account: Account, asset_id: str):
        self.pool_ALGO = 0
        self.pool_UCTZAR = 0
        self.total_lp_tokens = 0
        self.lp_tokens = {}
        self.pool_account = pool_account
        self.asset_id = asset_id

    def add_liquidity(
        self, provider: Account, amount_algo: float, amount_uctzar: float
    ):
        if provider.check_balance() < (
            amount_algo + 0.001
        ):  # Ensure balance for transaction fee
            print(f"{provider.address} has insufficient balance for the transaction.")
            return
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
            transactions=liquidity_txns, accounts=[provider, provider]
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
            transactions=[txn_1, txn_2], accounts=[trader, self.pool_account]
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

    def trade_uctzar_algo(self, trader: Account, amount_uctzar: float):

        # Trade fee calculation
        trade_fee = amount_uctzar * 0.003  # 0.3% fee
        net_amount_uctzar = amount_uctzar - trade_fee
        amount_algo = net_amount_uctzar / 2

        net_converted_amount = int(net_amount_uctzar * 1e2)

        txn_1 = AssetTransferTxn(
            sender=trader.address,
            receiver=self.pool_account.address,
            amt=net_converted_amount,  # Convert UCTZAR to its smallest unit (2 decimals)
            index=self.asset_id,
            sp=self.pool_account.algod_client.suggested_params(),
        )

        txn_2 = PaymentTxn(
            sender=self.pool_account.address,
            receiver=trader.address,
            amt=int(amount_algo / Account.algo_conversion),  # Convert Algo to MicroAlgo
            sp=self.pool_account.algod_client.suggested_params(),
        )

        signed_txns = process_atomic_transactions(
            transactions=[txn_1, txn_2], accounts=[trader, self.pool_account]
        )

        txid = self.pool_account.algod_client.send_transactions(signed_txns)
        _ = transaction.wait_for_confirmation(self.pool_account.algod_client, txid)

        # Update pool balances and LP tokens
        self.pool_ALGO -= amount_algo
        self.pool_UCTZAR += net_amount_uctzar
        lp_token_amount = net_amount_uctzar + amount_algo
        self.total_lp_tokens += lp_token_amount
        self.lp_tokens[trader.address] = (
            self.lp_tokens.get(trader.address, 0) + lp_token_amount
        )
        print(f"LP Tokens for {trader.address}: {self.lp_tokens[trader.address]}")
        print(f"{trader.address} traded {amount_uctzar} UCTZAR for {amount_algo} ALGO.")
        print(f"Trade fee of {trade_fee} UCTZAR added to the pool.")

    def remove_liquidity(self, provider: Account):
        tokens = self.lp_tokens[provider.address]
        if tokens == 0:
            print("No LP tokens to remove.")
            return

        provider_share = tokens / self.total_lp_tokens
        algo_share = provider_share * self.pool_ALGO
        uctzar_share = provider_share * self.pool_UCTZAR

        txn_1 = PaymentTxn(
            sender=self.pool_account.address,
            receiver=provider.address,
            amt=int(algo_share * 1e6),  # Convert ALGO to microAlgos
            sp=self.pool_account.algod_client.suggested_params(),
        )

        txn_2 = AssetTransferTxn(
            sender=self.pool_account.address,
            receiver=provider.address,
            amt=int(uctzar_share * 1e2),  # Convert UCTZAR to smallest unit (2 decimals)
            index=self.asset_id,
            sp=self.pool_account.algod_client.suggested_params(),
        )

        signed_txns = process_atomic_transactions(
            transactions=[txn_1, txn_2], accounts=[self.pool_account, self.pool_account]
        )

        txid = self.pool_account.algod_client.send_transactions(signed_txns)
        _ = transaction.wait_for_confirmation(self.pool_account.algod_client, txid)

        # Update pool balances and LP tokens
        self.pool_ALGO -= algo_share
        self.pool_UCTZAR -= uctzar_share
        self.total_lp_tokens -= tokens
        del self.lp_tokens[provider.address]

        print(
            f"{provider.address} withdrew {algo_share} ALGO and {uctzar_share} UCTZAR."
        )


# Utility Functions
###############################################################################################################################
def process_atomic_transactions(
    transactions: List[AssetTransferTxn], accounts: List[Account]
) -> List[SignedTransaction]:
    signed_txns = []
    gid = transaction.calculate_group_id(transactions)
    for txn, account in zip(transactions, accounts):
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

    # Wait for transaction confirmation
    transaction.wait_for_confirmation(manager_address.algod_client, txid)

    # Fetch the asset ID from the account information
    account_info = manager_address.algod_client.account_info(manager_address.address)
    asset_id = None
    for asset in account_info.get("created-assets", []):
        if asset["params"]["name"] == "South African Rand Stablecoin":
            asset_id = asset["index"]
            print("UCTZAR asset ID:", asset_id)
            break

    if asset_id is None:
        raise Exception("Asset creation failed; asset ID not found.")

    return asset_id


def opt_in_asset(trader: Account, asset_id: str):
    params = trader.algod_client.suggested_params()
    opt_in_txn = AssetOptInTxn(sender=trader.address, sp=params, index=asset_id)
    signed_opt_in_txn = opt_in_txn.sign(trader.private_key)
    txid = trader.algod_client.send_transaction(signed_opt_in_txn)
    print(f"{trader.address} opted into asset ID {asset_id}, TXID: {txid}")


def opt_out_asset(trader: Account, asset_id: str, pool: LiquidityPool):
    """
    Opts out the user from the asset, converting their UCTZAR holdings to ALGOs
    and sending the equivalent ALGO amount to their account before opting out.
    """
    # Check user's remaining UCTZAR in the pool
    uctzar_balance = pool.lp_tokens.get(trader.address, 0)
    if uctzar_balance == 0:
        print(f"{trader.address} has no remaining UCTZAR in the pool to withdraw.")
        return

    # Calculate equivalent ALGO amount based on 1 UCTZAR = 0.5 ALGO
    algo_amount = uctzar_balance * 0.5

    # Check if pool has enough ALGO to cover this amount
    if algo_amount > pool.pool_ALGO:
        print("Not enough liquidity in the pool to cover this opt-out payout in ALGOs.")
        return

    params = trader.algod_client.suggested_params()

    # Step 1: Transfer equivalent ALGOs from Pool to User
    payout_txn = PaymentTxn(
        sender=pool.pool_account.address,
        receiver=trader.address,
        amt=int(algo_amount * 1e6),  # Convert to microAlgos
        sp=params,
    )

    # Step 2: Create the Opt-Out transaction for UCTZAR
    opt_out_txn = AssetTransferTxn(
        sender=trader.address,
        sp=params,
        receiver=trader.address,
        amt=0,  # Required to opt-out of the asset
        index=asset_id,
    )

    signed_txns = process_atomic_transactions(
        transactions=[payout_txn, opt_out_txn], accounts=[pool.pool_account, trader]
    )

    trader.algod_client.send_transactions(signed_txns)
    print(f"{trader.address} opted out of asset ID {asset_id}.")

    # Update the pool's state
    pool.pool_ALGO -= algo_amount
    pool.total_lp_tokens -= uctzar_balance
    del pool.lp_tokens[trader.address]


def distribute_initial_uctzar(
    manager: Account, recipient: Account, asset_id: str, amount: int
):
    """
    Distribute an initial supply of UCTZAR from the manager to the liquidity pool account.

    Parameters:
    - manager: Account that created the UCTZAR asset.
    - recipient: Account of the liquidity pool.
    - asset_id: The UCTZAR asset ID.
    - amount: The amount of UCTZAR to transfer (in the smallest unit, e.g., 1 = 0.01 UCTZAR).
    """
    params = manager.algod_client.suggested_params()
    txn = AssetTransferTxn(
        sender=manager.address,
        receiver=recipient.address,
        amt=amount,
        index=asset_id,
        sp=params,
    )

    signed_txn = txn.sign(manager.private_key)
    txid = manager.algod_client.send_transaction(signed_txn)
    print(f"Distributed {amount * 0.01} UCTZAR to liquidity pool, TXID: {txid}")
    _ = transaction.wait_for_confirmation(manager.algod_client, txid)


# Add this function to distribute UCTZAR to all participants
def distribute_uctzar_to_participants(
    manager: Account, participants: List[Account], asset_id: str, amount: int
):
    params = manager.algod_client.suggested_params()
    for participant in participants:
        txn = AssetTransferTxn(
            sender=manager.address,
            receiver=participant.address,
            amt=amount,
            index=asset_id,
            sp=params,
        )
        signed_txn = txn.sign(manager.private_key)
        txid = manager.algod_client.send_transaction(signed_txn)
        print(
            f"Distributed {amount * 0.01} UCTZAR to {participant.address}, TXID: {txid}"
        )
        transaction.wait_for_confirmation(manager.algod_client, txid)


# Main Simulation Function
def run_simulation():

    accounts = [
        {
            "address": "N6F3F2ZDMKVGLHBQJZPCDFKEBTJXKL72IFRPEKC3PF3C3XMHOA7OHSPCGE",
            "mnemonic_phrase": "wonder vote tourist escape sugar square arctic nice convince piece sea change forward tissue bottom please another door exclude start innocent system flat about blanket",
            "private_key": "6H/9y9Fk7E1nYZV8GemDY+Iti0tjpkxY0J1KTTpzE2tvi7LrI2KqZZwwTl4hlUQM03Uv+kFi8ihbeXYt3YdwPg==",
        },
        {
            "address": "ETTIX3ZF4C4QZWBCQMJNOW3YC7YATYQWVX2JRBDDCBISDL4LJ42G2LZP6A",
            "mnemonic_phrase": " category salmon alarm animal relief bright craft please occur picnic they milk spike drama regret pilot sister pact staff clean exchange staff shop abandon diamond",
            "private_key": "IZmvC5CgWnBAZqbGDCnByejoCJX2pEyuJ6ilUidQ1xgk5ovvJeC5DNgigxLXW3gX8AniFq30mIRjEFEhr4tPNA==",
        },
        {
            "address": "2XDDAOR3X5XGJTJ6R5FD6XTCALL2LTPQJVYM7HZLCAPQLSIJJAOUYHTGGQ",
            "mnemonic_phrase": "dynamic wisdom oxygen chair ozone primary about blade wood odor trick repeat side load ankle they habit congress ridge radar foil like winner absent record",
            "private_key": "JhK/PF1Cz6oOABfpT+bQa/vjCyaB4EHDC3MLO60Gfr/VxjA6O79uZM0+j0o/XmIC16XN8E1wz58rEB8FyQlIHQ==",
        },
        {
            "address": "SDEQISAHS7N2K4PGYVXGOKHGIQW225BH4IORNVE6LISK3M64P72Q6PX6UQ",
            "mnemonic_phrase": "immune lyrics violin category destroy onion among buyer dune swap chuckle shadow correct warrior odor define cry suffer what tell observe swap infant above globe",
            "private_key": "jVuh6EMSHmv+YB8g0jZRTEwY3SeTOakptvPtPUxta46QyQRIB5fbpXHmxW5nKOZELa10J+IdFtSeWiSts9x/9Q==",
        },
        {
            "address": "WQ7JCTY4KHCBCD6P3QEHEQXJCWIT34EFNNG5M32ILKSDTGY5KZ6EACFXCE",
            "mnemonic_phrase": "veteran barely earth lake axis depth erase receive result culture column bag common excuse south tail dad survey visit sound manual ocean doll abstract hamster",
            "private_key": "mafEisp3iOyMibO+ZY1bGDEXPAVa3beptun9vMNjFui0PpFPHFHEEQ/P3AhyQukVkT3whWtN1m9IWqQ5mx1WfA==",
        },
    ]

    lp_account = Account(**accounts[0])
    provider_account_one = Account(**accounts[1])
    provider_account_two = Account(**accounts[2])
    trader_account_one = Account(**accounts[3])
    trader_account_two = Account(**accounts[4])

    # Step 1: Create UCTZAR asset by the liquidity provider account
    asset_id = create_uctzar_asset(manager_address=lp_account)

    # Step 2: Opt-in for UCTZAR asset for pool, providers, and traders
    opt_in_asset(trader=lp_account, asset_id=asset_id)
    opt_in_asset(trader=trader_account_one, asset_id=asset_id)
    opt_in_asset(trader=trader_account_two, asset_id=asset_id)
    opt_in_asset(trader=provider_account_one, asset_id=asset_id)
    opt_in_asset(trader=provider_account_two, asset_id=asset_id)

    # Step 3: Fund the liquidity pool itself with an initial supply of UCTZAR
    initial_uctzar_amount = 500  # Example: 50 UCTZAR in smallest unit (2 decimals)
    distribute_initial_uctzar(
        manager=lp_account,
        recipient=lp_account,
        asset_id=asset_id,
        amount=initial_uctzar_amount,
    )

    # Step 4: Distribute initial UCTZAR to participants for trading and liquidity
    distribute_uctzar_to_participants(
        manager=lp_account,
        participants=[
            provider_account_one,
            provider_account_two,
            trader_account_one,
            trader_account_two,
        ],
        asset_id=asset_id,
        amount=100,  # Example: 1.00 UCTZAR in smallest unit
    )

    # Step 4: Initialize the liquidity pool
    pool = LiquidityPool(pool_account=lp_account, asset_id=asset_id)

    # Step 5: Add liquidity to the pool from provider accounts
    pool.add_liquidity(provider=provider_account_one, amount_algo=0.5, amount_uctzar=1)
    pool.add_liquidity(provider=provider_account_two, amount_algo=0.5, amount_uctzar=1)

    # Step 6: Traders trade ALGOs for UCTZAR
    pool.trade_algo_uctzar(trader=trader_account_one, amount_algo=0.1)
    pool.trade_uctzar_algo(trader=trader_account_two, amount_uctzar=0.2)

    # Step 7: Liquidity providers remove liquidity from the pool
    pool.remove_liquidity(provider=provider_account_one)
    pool.remove_liquidity(provider=provider_account_two)

    # Step 8: Opt-out of UCTZAR asset and withdraw funds
    opt_out_asset(trader=lp_account, asset_id=asset_id, pool=pool)
    opt_out_asset(trader=trader_account_one, asset_id=asset_id, pool=pool)
    opt_out_asset(trader=trader_account_two, asset_id=asset_id, pool=pool)
    opt_out_asset(trader=provider_account_one, asset_id=asset_id, pool=pool)
    opt_out_asset(trader=provider_account_two, asset_id=asset_id, pool=pool)


# Run the simulation
if __name__ == "__main__":
    run_simulation()
