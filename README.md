# Algorand Stokvel and Decentralized Exchange (DEX) Simulation

This repository contains two Python scripts that simulate different financial systems on the Algorand blockchain. Each script demonstrates the functionality of a specific decentralized application:

1. **Stokvel Simulation**: Implements a stokvel, a collective savings system where participants contribute funds to a shared pool, which is distributed among them on a rotational basis.
2. **Decentralized Exchange (DEX) Simulation**: Implements a simple DEX with a liquidity pool that allows traders to swap ALGOs and UCTZAR (a simulated stablecoin).

Both simulations leverage the Algorand blockchain to demonstrate decentralized financial applications in a secure and transparent manner. Below, you will find a detailed explanation of each simulation and instructions on how to run them.


## Setting Up a Virtual Environment and Installing Requirements

Before running the applications, you will need to create a virtual environment and install the project dependencies.

**Create a Virtual Environment**

In your terminal, navigate to the project directory and create a virtual environment named `venv`:

```bash
python3 -m venv venv
```

This command will create a folder named `venv` containing all necessary files for the virtual environment.

**Activate the Virtual Environment**:

**On macOS/Linux**

```bash
source venv/bin/activate
```

**On Windows**

```bash
.\venv\Scripts\activate
```

**Install Required Dependencies**:

Once the virtual environment is activated, install the dependencies for this application. Run:

```bash
pip install -r requirements.txt
```

This installs the Algorand SDK, which the application uses for blockchain interactions.

## 1. Stokvel Simulation

The Stokvel simulation demonstrates a group savings scheme on the Algorand blockchain. In this scenario, participants contribute to a shared pool periodically. The collected funds are then distributed to one participant in each round, with this process rotating among all members until each has received a payout.

### Key Components

- **Account Management**: Each participant has an Algorand account managed by the `Account` class.
- **Transaction Types**: Two main transaction types are supported:
  - **Single Signature Transaction**: A standard transaction with one sender.
  - **Multisignature Transaction**: Requires multiple signatures for transactions, which simulates a more secure group decision-making process.
- **Custom Errors**: Custom exceptions for invalid addresses, insufficient funds, and invalid command-line arguments.

### Workflow

1. **Account Creation**: Generates accounts for each participant, each with a unique Algorand address and a starting balance funded via the Algorand test dispenser.

2. **Multisignature Account Setup**: A multisignature account is created to manage the pool of contributions. A threshold of signatures is required to release the funds from this multisig account.

3. **Monthly Contributions**: Each participant contributes a fixed amount of ALGO to the shared pool on a set day of the month.

4. **Payout Distribution**: On the following day, the pooled funds are distributed to a randomly selected participant, simulating a rotational payout system. Only if a threshold of participants agrees by signing the transaction does the payout proceed.

5. **Looping Simulation**: The simulation continues over a predefined period, allowing each participant to receive a payout until all have benefited.

### Running the Stokvel Simulation

```bash
python stokvel_simulation.py --time <day_of_month>
```

- **`--time`**: Specify the day of the month on which contributions are made (e.g., 10). Default is 10.

---

## 2. Decentralized Exchange (DEX) Simulation

The DEX simulation illustrates the workflow of a decentralized exchange with a liquidity pool, allowing participants to add liquidity and perform trades between ALGO and a simulated stablecoin, UCTZAR.

### Key Components

- **Liquidity Pool**: Managed by the `LiquidityPool` class, which maintains two main asset balances, ALGOs and UCTZAR. Liquidity providers add assets to this pool and receive LP tokens representing their share.
- **Trading Mechanism**: Allows users to trade between ALGOs and UCTZAR within the pool. A small transaction fee is deducted from each trade, rewarding liquidity providers.
- **LP Tokens**: Issued to liquidity providers in proportion to their contribution. These tokens represent a share in the pool and can be redeemed when removing liquidity.

### Workflow

1. **Asset Creation (UCTZAR)**: A stablecoin asset (UCTZAR) is created and managed by a central account, which distributes an initial supply to the liquidity pool and participating traders.

2. **Opt-In for UCTZAR Asset**: Each participant must opt into the UCTZAR asset to hold and trade it.

3. **Liquidity Provision**: Liquidity providers deposit a mix of ALGOs and UCTZAR into the pool. In exchange, they receive LP tokens, representing their share in the pool’s liquidity.

4. **Trading**: Traders can swap between ALGOs and UCTZAR through the liquidity pool. Each trade incurs a fee (e.g., 0.3%) that is added back into the pool, rewarding LP token holders indirectly.

5. **Removing Liquidity**: Liquidity providers can withdraw their share from the pool, receiving an amount of ALGOs and UCTZAR proportional to their LP tokens.

6. **Opt-Out of UCTZAR**: Traders and providers can opt out of the UCTZAR asset, withdrawing all remaining balances before removing themselves from the asset registry.

### Running the DEX Simulation

```bash
python dex_simulation.py
```

This command runs a full cycle of the DEX simulation, including asset creation, liquidity provision, trading, and withdrawal.