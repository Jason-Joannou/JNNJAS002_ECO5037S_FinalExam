import argparse
from typing import Any, Dict, List, Optional, Tuple

from algosdk import account, encoding, error, mnemonic, transaction
from algosdk.v2client import algod


class InvalidAddressError(Exception):
    """
    Custom exception raised when an invalid address is encountered.
    """

    def __init__(self, message) -> None:
        """
        Initialize InvalidAddressError with a custom message.

        Parameters:
            message (str): Error message to be displayed. Defaults to a generic message.
        """
        super().__init__(message)


class InsufficientFundsError(Exception):
    """
    Custom exception raised when insufficient funds are available for a transaction.
    """

    def __init__(self, message) -> None:
        """
        Initialize InsufficientFundsError with a custom message.

        Parameters:
            message (str): Error message to be displayed. Defaults to a generic message.
        """
        super().__init__(message)


class Account:

    algod_address = "https://testnet-api.algonode.cloud"
    algod_client = algod.AlgodClient("", algod_address)
    algo_conversion = 0.000001

    def __init__(
        self,
        address: str,
        private_key: Optional[str] = None,
        mnemonic: Optional[str] = None,
    ) -> None:
        self.address = address
        self.private_key = private_key
        self.mnemonic = mnemonic

    def account_info(self) -> Dict[str, Any]:
        try:
            return self.algod_client.account_info(self.address)
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return {}

    def check_balance(self) -> int:
        account_info = self.account_info()
        return account_info["amount"] * self.algo_conversion


class Transaction:
    def __init__(self, sender: Account, receiver: Account, amount: int) -> None:
        self.sender = sender
        self.receiver = receiver
        self.amount = amount

    def pay(self, note: str):
        if self.sender.check_balance() < self.amount:
            raise InsufficientFundsError(
                f"Insufficient funds for {self.sender.address}"
            )

        converted_ammount = int(self.amount / self.sender.algo_conversion)
        unsigned_txn = transaction.PaymentTxn(
            sender=self.sender.address,
            sp=self.sender.algod_client.suggested_params(),
            receiver=self.receiver,
            amt=converted_ammount,  # Amount variable is measured in MicroAlgos. i.e. 1 ALGO = 1,000,000 MicroAlgos
            note=encoding.encode(note),
        )

        signed_txn = unsigned_txn.sign(self.sender.private_key)

        txid = self.sender.algod_client.send_transaction(signed_txn)

        _ = transaction.wait_for_confirmation(self.sender.algod_client, txid)

        print(f"Successfully submitted transaction with txID: {txid}")
        print(f"Sender: {self.sender.address}")
        print(f"Receiver: {self.receiver.address}")
        print(f"Amount: {self.amount} Algoes")
        print(f"Note: {note}")


# Utility functions
#################################################################################################################


def load_account(address: str, private_key: str, mnemonic: str) -> Account:
    """
    Load an account with the provided address, private key, passphrase, and save it to file if specified.

    Parameters:
        address (str): The address of the account.
        private_key (str): The private key associated with the account.
        pass_phrase (str): The passphrase generated from the private key.
        to_file (bool): Flag indicating whether to save the account to a txt file.

    Returns:
        Account: An instance of the Account class representing the loaded account.
    """
    return Account(address=address, private_key=private_key, mnemonic=mnemonic)


def generate_account(n_accounts: int = 5) -> List[Account]:
    """
    Generate a list of new accounts with the specified number and optionally save them to file.

    Parameters:
        n_accounts (int): The number of accounts to generate.

    Returns:
        List[Account]: A list of Account instances representing the generated accounts.
    Raises:
        InvalidAddressError: If an invalid address is encountered during account generation.
    """
    accounts = []
    for i in range(1, n_accounts + 1):
        # generate an accountp
        private_key, address = account.generate_account()
        mnemonic = mnemonic.from_private_key(private_key)

        user_account = load_account(
            address=address, private_key=private_key, mnemonic=mnemonic
        )
        accounts.append(user_account)
    return accounts


def produce_multisig_stokvel_account(
    threshold: int,
    accounts: List[Account],
    version: int = 1,
):
    try:
        multi_sig_address = [account.address for account in accounts]
        multi_sig_account = transaction.Multisig(
            version=version,
            threshold=threshold,
            addresses=multi_sig_address,
        )
        multi_sig_account.validate()

        return Account(address=multi_sig_account.address())

    except error.UnknownMsigVersionError as e:
        print(f"Error: {e}")
    except error.InvalidThresholdError as e:
        print(f"Error: {e}")
    except error.MultisigAccountSizeError as e:
        print(f"Error: {e}")
    except error.ConfirmationTimeoutError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
