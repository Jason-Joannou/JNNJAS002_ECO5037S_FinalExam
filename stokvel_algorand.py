import argparse
import random
import time
import webbrowser
from typing import Any, Dict, List, Optional

from algosdk import account, error, mnemonic, transaction
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


class InvalidCLIArgumentsError(Exception):
    """
    Custom exception raised when invalid command-line arguments are provided.
    """

    def __init__(self, message) -> None:
        """
        Initialize InvalidCLIArgumentsError with a custom message.

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
        mnemonic_phrase: Optional[str] = None,
    ) -> None:
        """
        Initialize an Account instance with the specified address, private key, and mnemonic phrase.

        Parameters:
            address (str): The address of the account.
            private_key (Optional[str]): The private key associated with the account, default is None.
            mnemonic_phrase (Optional[str]): The mnemonic phrase for the account, default is None.
        """
        self.address = address
        self.private_key = private_key
        self.mnemonic_phrase = mnemonic_phrase

    def account_info(self) -> Dict[str, Any]:
        """
        Retrieve account information from the Algorand blockchain.

        Returns:
            Dict[str, Any]: A dictionary containing information about the account,
            such as balance and status. If an error occurs during retrieval, an empty
            dictionary is returned and an error message is printed.
        """
        try:
            return self.algod_client.account_info(self.address)
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return {}

    def check_balance(self) -> int:
        """
        Retrieve the balance of the account in ALGOs.

        Returns:
            int: The balance of the account in ALGOs.
        """
        account_info = self.account_info()
        return account_info["amount"] * self.algo_conversion

    def fund_address(self) -> None:
        """
        Ensures that the account is funded with sufficient ALGOs to transact on the Algorand blockchain.

        This method checks the balance of the account. If the balance is less than or equal to 1 ALGO,
        it prompts the user to fund the account using the Algorand test dispenser and opens the dispenser
        URL in a web browser. It then repeatedly checks the balance until the account is funded.

        If the balance is sufficient, it confirms that the account is funded and prints the current balance.
        """
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


class SingleSigTransaction:
    def __init__(
        self,
        sender: Account,
        receiver: Account,
        amount: int,
    ) -> None:
        """
        Initialize a SingleSigTransaction with the specified sender, receiver, and amount.

        Parameters:
            sender (Account): The account that will send the transaction.
            receiver (Account): The account that will receive the transaction.
            amount (int): The amount to be transferred in ALGOs.
        """

        self.sender = sender
        self.receiver = receiver
        self.amount = amount

    def pay(self, note: str):
        """
        Executes a single signature payment transaction on the Algorand blockchain.

        This method checks if the sender has sufficient funds to cover the transaction amount
        and funds the account if necessary. It then creates, signs, and sends a payment transaction
        from the sender to the receiver. The transaction is confirmed on-chain, and relevant
        transaction details are printed.

        Parameters:
            note (str): A note to include with the transaction, encoded in UTF-8.

        Raises:
            Exception: If an error occurs during the transaction process.
        """
        try:

            if self.sender.check_balance() < self.amount:
                print(f"Insufficient funds for {self.sender.address}")
                self.sender.fund_address()

            converted_ammount = int(self.amount / self.sender.algo_conversion)
            unsigned_txn = transaction.PaymentTxn(
                sender=self.sender.address,
                sp=self.sender.algod_client.suggested_params(),
                receiver=self.receiver.address,
                amt=converted_ammount,  # Amount variable is measured in MicroAlgos. i.e. 1 ALGO = 1,000,000 MicroAlgos
                note=note.encode("utf-8"),
            )

            signed_txn = unsigned_txn.sign(self.sender.private_key)

            txid = self.sender.algod_client.send_transaction(signed_txn)

            _ = transaction.wait_for_confirmation(self.sender.algod_client, txid)

            print(f"Successfully submitted transaction with txID: {txid}")
            print(f"Sender: {self.sender.address}")
            print(f"Receiver: {self.receiver.address}")
            print(f"Amount: {self.amount} Algoes")
            print(f"Note: {note}")
        except Exception as e:
            print(f"Error in SingleSig: {e}")


class MultiSigTransaction:

    def __init__(
        self,
        multisig_account: Account,
        receiver: Account,
        multisig_participants: List[Account],
        amount: int,
        threshold: int,
    ) -> None:
        """
        Initialize a MultiSigTransaction with the specified sender, receiver, participants, amount and threshold.

        Parameters:
            multisig_account (Account): The account that will send the transaction.
            receiver (Account): The account that will receive the transaction.
            multisig_participants (List[Account]): The participants that will sign the transaction.
            amount (int): The amount to be transferred.
            threshold (int): The required number of signatures to authorize the transaction.
        """
        self.sender = multisig_account
        self.receiver = receiver
        self.participants = multisig_participants
        self.amount = amount
        self.threshold = threshold
        self.version = 1

    def pay(self, note: str):
        """
        Executes a multisignature payment transaction on the Algorand blockchain.

        This method checks if the sender has sufficient funds to cover the transaction amount
        and funds the account if necessary. It then creates, signs, and sends a payment transaction
        from the sender to the receiver. The transaction is confirmed on-chain, and relevant
        transaction details are printed.

        Parameters:
            note (str): A note to include with the transaction, encoded in UTF-8.

        Raises:
            InsufficientFundsError: If the sender does not have sufficient funds to cover the transaction amount.
            Exception: If an error occurs during the transaction process.
        """
        try:
            if self.sender.check_balance() < self.amount:
                raise InsufficientFundsError(
                    f"Insufficient funds for {self.sender.address}"
                )
            converted_amount = int(self.amount / Account.algo_conversion)
            multi_sig_addresses = [
                participant.address for participant in self.participants
            ]

            multi_sig_txn = transaction.Multisig(
                version=self.version,
                threshold=self.threshold,
                addresses=multi_sig_addresses,
            )
            multi_sig_txn.validate()

            unsigned_msig_txn = transaction.PaymentTxn(
                sender=self.sender.address,
                sp=self.sender.algod_client.suggested_params(),
                receiver=self.receiver.address,
                amt=converted_amount,
                note=note.encode("utf-8"),
            )

            msig_txn = transaction.MultisigTransaction(unsigned_msig_txn, multi_sig_txn)

            for i in range(self.threshold):
                msig_txn.sign(self.participants[i].private_key)
            txid = self.sender.algod_client.send_transaction(msig_txn)
            _ = transaction.wait_for_confirmation(self.sender.algod_client, txid)

            print(f"Successfully submitted transaction with txID: {txid}")
            print(f"Sender: {self.sender.address}")
            print(f"Receiver: {self.receiver.address}")
            print(f"Amount: {self.amount} Algoes")
            print(f"Note: {note}")

        except Exception as e:
            print(f"Error in MultiSig: {e}")


# Utility functions
#################################################################################################################


def load_account(address: str, private_key: str, mnemonic_phrase: str) -> Account:
    """
    Load an account with the provided address, private key, passphrase, and save it to file if specified.

    Parameters:
        address (str): The address of the account.
        private_key (str): The private key associated with the account.
        mnemonic_phrase (str): The mnemonic phrase for the account.

    Returns:
        Account: An instance of the Account class representing the loaded account.
    """
    return Account(
        address=address, private_key=private_key, mnemonic_phrase=mnemonic_phrase
    )


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
        mnemonic_phrase = mnemonic.from_private_key(private_key)

        user_account = load_account(
            address=address, private_key=private_key, mnemonic_phrase=mnemonic_phrase
        )
        print("Account Address:", user_account.address)
        print("Account Mnemonic Phrase:", mnemonic_phrase)
        print("Account Private Key:", private_key)
        user_account.fund_address()
        accounts.append(user_account)
    return accounts


def produce_multisig_stokvel_account(
    threshold: int,
    accounts: List[Account],
    version: int = 1,
):
    """
    Produce a multisig account with the specified threshold and list of accounts.

    Parameters:
        threshold (int): The minimum number of signatures required to authorize a transaction.
        accounts (List[Account]): A list of Account instances representing the participants in the multisig account.
        version (int): The version of the multisig account, defaults to 1.

    Returns:
        Account: The multisig account.

    Raises:
        UnknownMsigVersionError: If the version of the multisig account is unknown.
        InvalidThresholdError: If the threshold is invalid.
        MultisigAccountSizeError: If the size of the multisig account is invalid.
        ConfirmationTimeoutError: If the confirmation request times out.
        Exception: If any other error occurs.
    """
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


def test_transactions():

    # accounts = generate_account()
    """
    Test transactions between accounts.

    This function tests transactions between accounts, first by generating a list of accounts, then by creating a multisig account and making payments to it from each account, and finally by making a multisig transaction from the multisig account to one of the accounts.
    """
    accounts = [
        {
            "address": "XIYVUEEH6BAUJPZDRMWIEINY32N7XWVSBABTD2NZALUKW6UR3BEBRZ4LPA",
            "mnemonic_phrase": "usage toy repeat muscle neck matter gloom minute quantum bracket will unfair alley target effort book oval rib portion boy margin west source abandon dirt",
            "private_key": "fJ95bRnZSSVuTI16tUb20U6Dd9eIGe08rlCr8cPlAxq6MVoQh/BBRL8jiyyCIbjem/vasggDMem5AuirepHYSA==",
        },
        {
            "address": "ZJLDM4WFX2RBZM5DCWD4FZ364H3MW6X2ELNZI3BVTXDB5FMO4QYYEF5LYY",
            "mnemonic_phrase": "wood video relax shop palm repeat bomb lawsuit example exit health assume umbrella you near dice delay odor chalk drastic plastic now exchange about fetch",
            "private_key": "6fc8amusz9omI35z+lPU3hD2/HNyPc9J5kskBNNc1mnKVjZyxb6iHLOjFYfC537h9st6+iLblGw1ncYelY7kMQ==",
        },
        {
            "address": "THSRW54PN3QB5HWZOTEKHSTTITDI4FQXP5EHKOVCXCEKBPHDDP4CTKERDY",
            "mnemonic_phrase": "bachelor boring congress beauty speed plastic brisk ranch uphold miss remember infant salute hungry impose enforce shadow drum chapter switch cloth regular lawn about frozen",
            "private_key": "iXgGXjqBaJiKg7F2d2NrNWdfvT0uSibm0EzC7RXTwm+Z5Rt3j27gHp7ZdMijynNExo4WF39IdTqiuIigvOMb+A==",
        },
        {
            "address": "2HZHZSFC7MUNLCXF2OAJRCJQGRXZEXGYV5FIBZOM277WYYP5JVZBE43WXQ",
            "mnemonic_phrase": "major waste this fox tissue first adult indoor vacant wrong fluid vague install sure toss diagram summer demise fun fix fiscal auto pet absorb wink",
            "private_key": "M+y9wcVl8V15AHODr3+zCr86aLf8PMmWDryAxSs+bNTR8nzIovso1Yrl04CYiTA0b5Jc2K9KgOXM1/9sYf1Ncg==",
        },
        {
            "address": "UFM4KJQYQKBDHADZKPOW477IZMD7R5P2556EVDERUV4E6EQAE27C42T6WU",
            "mnemonic_phrase": "tonight bird salon process chicken beach denial dragon legal risk arena track huge room syrup spoon lucky adapt wash install rent slight north abandon bean",
            "private_key": "JKcFfbnak01MB0L7m+4WaF6375ab0iXEwO5XJ9suyxKhWcUmGIKCM4B5U91uf+jLB/j1+u98SoyRpXhPEgAmvg==",
        },
    ]
    accounts = [Account(**account) for account in accounts]
    threshold = round(0.8 * len(accounts))

    multisig_account = produce_multisig_stokvel_account(
        threshold=threshold, accounts=accounts, version=1
    )
    amount = 0.5
    sum_ammount = 0
    for account in accounts:
        SingleSigTransaction(sender=account, receiver=multisig_account, amount=0.5).pay(
            note=f"Payment made from participant {account.address} to stokvel address {multisig_account.address}"
        )
        sum_ammount += amount

    MultiSigTransaction(
        multisig_account=multisig_account,
        receiver=accounts[0],
        multisig_participants=accounts,
        amount=sum_ammount,
        threshold=threshold,
    ).pay(
        note=f"Payment made from stokvel address {multisig_account.address} to participant {accounts[0].address}"
    )


def run_payment_simulation(
    time_t: int, accounts: List[Account], multisig_account: Account, amount: int
) -> None:
    """
    Run a simulation of a stokvel payment system.

    Parameters:
    time_t (int): The day of the month when the contributions are made.
    accounts (List[Account]): A list of Account objects that are part of the stokvel.
    multisig_account (Account): The Account object that manages the stokvel.
    amount (int): The amount of ALGO that each participant contributes to the stokvel.

    Returns:
    None
    """
    successful_payments = set()
    i = 1
    sum_ammount = 0
    count_months = 1
    stop_simulation = False
    while i < 31 and not stop_simulation:
        print(f"This is day {i} of month {count_months}.")
        if i == time_t:
            print(f"Day {i} of month {count_months} is contribution day.")
            for account in accounts:
                SingleSigTransaction(
                    sender=account, receiver=multisig_account, amount=0.5
                ).pay(
                    note=f"Payment made from participant {account.address} to stokvel address {multisig_account.address}"
                )
                sum_ammount += amount

        if i == time_t + 1:
            print(f"Day {i} of month {count_months} is payout day.")
            signature_ammounts = 0
            payout_account = random.choice(accounts)
            if payout_account.address not in successful_payments:
                for account in accounts:
                    if (
                        input(
                            f"Account {account.address}, signature is needed to authorize the payout. Do you want to sign the transaction? (y/n)"
                        )
                        == "y"
                    ):
                        signature_ammounts += 1

                if signature_ammounts >= round(0.8 * len(accounts)):
                    MultiSigTransaction(
                        multisig_account=multisig_account,
                        receiver=payout_account,
                        multisig_participants=accounts,
                        amount=sum_ammount * 0.6,
                        threshold=round(0.8 * len(accounts)),
                    ).pay(
                        note=f"Payment made from stokvel address {multisig_account.address} to participant {payout_account.address}"
                    )
                    successful_payments.add(payout_account.address)
                    sum_ammount = sum_ammount - sum_ammount * 0.6

        if len(successful_payments) == 5:
            for account in accounts:
                if input("Do you want to continue? (y/n)") == "n":
                    stop_simulation = True  # Set the flag to True to stop both loops
                    break  # Break out of the inner loop
        if i == 30:
            i = 0
            count_months += 1
        if count_months == 13:
            count_months = 1

        i += 1


def main():
    """
    Run a Stokvel payment simulation.

    This function creates a list of 5 Account objects from hardcoded addresses, mnemonic phrases, and private keys.
    It then creates a multisig account from these 5 accounts with a threshold of 80% (4 out of 5 accounts).
    The function runs a simulation of a Stokvel payment system, where each account contributes 0.5 ALGO to the
    multisig account on a specified day of the month (default is 10), and a random account receives a payout of
    60% of the total contributions on the next day.
    The simulation continues until all 5 accounts have successfully received a payout.
    """
    parser = argparse.ArgumentParser(description="Run a Stokvel payment simulation.")
    parser.add_argument(
        "-t",
        "--time",
        type=int,
        default=10,
        help="Day of the month when contributions are made (default is 10)",
    )
    args = parser.parse_args()

    accounts = [
        {
            "address": "XIYVUEEH6BAUJPZDRMWIEINY32N7XWVSBABTD2NZALUKW6UR3BEBRZ4LPA",
            "mnemonic_phrase": "usage toy repeat muscle neck matter gloom minute quantum bracket will unfair alley target effort book oval rib portion boy margin west source abandon dirt",
            "private_key": "fJ95bRnZSSVuTI16tUb20U6Dd9eIGe08rlCr8cPlAxq6MVoQh/BBRL8jiyyCIbjem/vasggDMem5AuirepHYSA==",
        },
        {
            "address": "ZJLDM4WFX2RBZM5DCWD4FZ364H3MW6X2ELNZI3BVTXDB5FMO4QYYEF5LYY",
            "mnemonic_phrase": "wood video relax shop palm repeat bomb lawsuit example exit health assume umbrella you near dice delay odor chalk drastic plastic now exchange about fetch",
            "private_key": "6fc8amusz9omI35z+lPU3hD2/HNyPc9J5kskBNNc1mnKVjZyxb6iHLOjFYfC537h9st6+iLblGw1ncYelY7kMQ==",
        },
        {
            "address": "THSRW54PN3QB5HWZOTEKHSTTITDI4FQXP5EHKOVCXCEKBPHDDP4CTKERDY",
            "mnemonic_phrase": "bachelor boring congress beauty speed plastic brisk ranch uphold miss remember infant salute hungry impose enforce shadow drum chapter switch cloth regular lawn about frozen",
            "private_key": "iXgGXjqBaJiKg7F2d2NrNWdfvT0uSibm0EzC7RXTwm+Z5Rt3j27gHp7ZdMijynNExo4WF39IdTqiuIigvOMb+A==",
        },
        {
            "address": "2HZHZSFC7MUNLCXF2OAJRCJQGRXZEXGYV5FIBZOM277WYYP5JVZBE43WXQ",
            "mnemonic_phrase": "major waste this fox tissue first adult indoor vacant wrong fluid vague install sure toss diagram summer demise fun fix fiscal auto pet absorb wink",
            "private_key": "M+y9wcVl8V15AHODr3+zCr86aLf8PMmWDryAxSs+bNTR8nzIovso1Yrl04CYiTA0b5Jc2K9KgOXM1/9sYf1Ncg==",
        },
        {
            "address": "UFM4KJQYQKBDHADZKPOW477IZMD7R5P2556EVDERUV4E6EQAE27C42T6WU",
            "mnemonic_phrase": "tonight bird salon process chicken beach denial dragon legal risk arena track huge room syrup spoon lucky adapt wash install rent slight north abandon bean",
            "private_key": "JKcFfbnak01MB0L7m+4WaF6375ab0iXEwO5XJ9suyxKhWcUmGIKCM4B5U91uf+jLB/j1+u98SoyRpXhPEgAmvg==",
        },
    ]
    accounts = [Account(**account) for account in accounts]
    threshold = round(0.8 * len(accounts))

    multisig_account = produce_multisig_stokvel_account(
        threshold=threshold, accounts=accounts, version=1
    )
    if args.time >= 30 or args.time <= 0:
        raise InvalidCLIArgumentsError("Day of the month must be between 1 and 29")
    run_payment_simulation(
        time_t=args.time,
        accounts=accounts,
        multisig_account=multisig_account,
        amount=0.5,
    )


if __name__ == "__main__":
    # test_transactions()
    # accounts = generate_account()
    main()
