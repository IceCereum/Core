"""
This is the main Cryptocurrency class. It has a the following categories and
methods:
    1. CATEGORY: Meta-Parameters
        1.1. set_metaparams - sets the metaparameters for the chain
        1.2. get_latest_block_metaparams - gets the current block's
                                           metaparameters
    2. CATEGORY: Create Block
        2.1 create_block - converts the current TXPOOL into a block and adds it
                           to the chain
    3. CATEGORY: Address Specific
        3.1 get_balance_of_addr - gets the balance of an address
        3.2 get_transactions_of_addr - gets all the transactions of an address
    4. CATEGORY: Add Transaction
        4.1 add_transaction - adds a transaction to TXPOOL without validating
                              the transaction parameters
        4.2 validate_add_transaction - validates transaction parameters, then
                                       adds to TXPOOL
    5. CATEGORY: Blockchain Specific
        5.1 get_complete_chain - gets the entire chain excluding TXPOOL
        5.2 get_TXPOOL - gets TXPOOL
    6. CATEGORY: Load Chain
        6.1 load_chain - loads the saved blockchain
"""
from math import exp
from pathlib import Path
from copy import deepcopy
from json import dump, load
from hashlib import sha3_256

from Blockchain.Block import Block, time_utc

class Cryptocurrency:
    def __init__(self, **kwargs):
        """
        If `create_genesis` is present, `address` and `amount` must be present
        as well. If `create_genesis` is not present, this just initialises a
        Cryptocurrency instance with the metaparameters

        Keyword Arguments:
            create_genesis (Bool): To create genesis or not. Default: False
            address (str): The address to send the coins to when creating
                genesis. Default: GENESIS_ADDRESS
            amount (float): The amount of coins to generate when creating
                genesis. Default: 100000
            blocks_path (Path): The directory where each block file (JSON) is
                stored. Default: Blocks/
        """
        self.index = 0 # This is the index of the latest block in the chain
        self.chain = [] # This is a list of all the blocks (check add_block for
                        # the structure of a block)

        # These are related to TXPOOL, the pool of all current transactions
        # before they are mined into the blockchain
        self.transaction_number = 0
        self.TXPOOL = {} # (check add_transaction for the structure of a
                         # transaction)


        # Metaparameters (Read Docs/How-Coins-Are-Introduced)

        # These are fixed. If they are to be altered, they must be updated in
        # the set_metaparameters method
        self._difficulty = 2
        self._percentage_of_transactions_rewarded = 0.1
        # These are changed in the set_metaparameters method
        self._mining_fees = 1
        self._reward_for_transaction = 1.5

        self.blocks_path = Path(kwargs.get("blocks_path", "Blocks"))
        self.blocks_path.mkdir(parents= True, exist_ok= True)

        create_genesis = kwargs.get("create_genesis", None)

        if create_genesis:
            address = kwargs.get("address", "GENESIS_ADDRESS")
            amount = float(kwargs.get("amount", 100000))

            # This is the genesis
            self.add_transaction(
                sendr_addr= "Genesis",
                recvr_addr= address,
                value= amount,
                mining_fee= 0.0,
                timestamp= time_utc())

            # This transaction is now made into a block
            self.create_block(mined_block_hash= "0", nonce= "0")


    ############################################################################
    ############################# META-PARAMETERS ##############################
    ############################################################################
    def set_metaparams(self):
        """
        Sets the metaparameters for the next TXPOOL of the chain right *before*
        a block is created. More of explanation can be found at
        Docs/How-Coins-Are-Introduced

        NOTE: The amount of time the TXPOOL accepts transactions before
        converting into a block is called T. For the sake of simplicity, this is
        "manually" mined by an API call. If this Cryptocurrency instance were to
        mine the block by itself, it would have to spawn a thread that mines the
        block every T units of time. This can be set up with asyncio or simple
        threading.

        Definitions:
            R: number of transactions in the previous block
            Mu: Mining Fees
            Tau: Reward for Rewarded-Transaction
            Rho: percentage of transactions rewarded (fixed = 0.1 i.e., 10%)

        Calculations:
            Mu = {
                    1                   | R <= 10
                    (e^(R-10)) / 10     | R > 10
            }

            Tau = 1.5 * Mu
            Tau = {
                    1.5                 | R <= 10
                    1.5*(e^(R-10) / 10) | R > 10
            }

        Returns:
            tuple:
                float: Mining Fees
                float: Reward for a Transaction
        """
        # Since this is called BEFORE the TXPOOL is reset,
        # self.transaction_number indicates the number of transactions in the
        # TXPOOL that is going to be added as a block to the chain; this is the
        # metaparameter R for the next TXPOOL.
        R = self.transaction_number

        print (R)

        Mu = None
        Tau = None

        if R <= 10:
            Mu = 1
        else:
            Mu = exp((R - 10)/10)

        Tau = 1.5 * Mu

        self._mining_fees = Mu
        self._reward_for_transaction = Tau

        print (self._mining_fees, self._reward_for_transaction)

        return (Mu, Tau)


    def get_latest_block_metaparams(self):
        """
        Get a dictionary of meta parameters about this block

        Returns:
            dict:
                ```
                {
                    "index"              : Index of the current block that is
                                           going to be created
                    "TXPOOL"             : All the transactions in the TXPOOL.
                                           Refer to `add_transaction()` to see
                                           the structure of each transaction
                    "prev_hash"          : The hash of the previous block
                    "difficulty"         : The difficulty of this block
                    "mining_fees"        : The mining fees of this block
                    "num_tx_TXPOOL"      : The number of transactions in the
                                           TXPOOL
                    "reward_for_tx"      : The reward for a transaction, if
                                           rewarded
                    "percent_tx_rewarded": The percentage of transactions that
                                           are rewarded
                }
                ```
        """
        meta_params = {
            "index" : self.index,
            "TXPOOL" : self.TXPOOL,
            "prev_hash" : self.chain[-1].block_hash,
            "difficulty" : self._difficulty,
            "mining_fees" : self._mining_fees,
            "num_tx_TXPOOL": self.transaction_number,
            "reward_for_tx" : self._reward_for_transaction,
            "percent_tx_rewarded" : self._percentage_of_transactions_rewarded
        }

        return meta_params


    ############################################################################
    ############################### CREATE BLOCK ###############################
    ############################################################################
    def create_block(self, mined_block_hash, nonce):
        """
        Creates a block on the blockchain (in self.chain) and writes a block
        file (JSON) to self.blocks_path.

        The format of each block is:
        ```
        {
            "block_index": index of this block,
            "previous_block_hash": the previous block's hash,
            "difficulty": the difficulty of this block,
            "nonce": the nonce used by the miner to meet difficulty,
            "mined_block_hash": the hash submitted by the miner,
            "percent_tx_rewarded": percentage of the transactions rewarded,
            "mining_fee": mining fee for all the transactions of this block,
            "reward_for_tx": reward for the rewarded transaction,
            "transactions": see `add_transaction()`,
            "timestamp": timestamp at which the block is added to the chain
        }
        ```

        Args:
            mined_block_hash (str): the hash that is submitted by the miner
            nonce (str): the nonce used by the miner to meet difficulty

        Returns:
            `block`: The newly generated block
        """

        if self.index != 0:
            previous_hash = self.chain[-1].block_hash
        else:
            previous_hash = 0

        block = Block(
            block_index = self.index,
            mined_block_hash = mined_block_hash,
            previous_block_hash = previous_hash,
            nonce = nonce,
            difficulty = self._difficulty,
            transactions = self.TXPOOL,
        )

        file_name = str(self.index) + ".json"
        output_json = self.blocks_path / Path(file_name)

        block_dict = {
            "block_index" : self.index,
            "previous_block_hash" : previous_hash,
            "difficulty" : self._difficulty,
            "nonce" : nonce,
            "mined_block_hash" : mined_block_hash,
            "percent_tx_rewarded" : self._percentage_of_transactions_rewarded,
            "mining_fee" : self._mining_fees,
            "reward_for_tx" : self._reward_for_transaction,
            "transactions" : self.TXPOOL,
            "timestamp" : block.timestamp
        }

        with open(output_json, 'w') as F:
            dump(block_dict, F, indent = 2)

        self.set_metaparams()

        self.index += 1

        # Reset TXPOOL
        self.TXPOOL = {}
        self.transaction_number = 0

        # Adding the block to the chain
        self.chain.append(block)

        return block


    ############################################################################
    ############################ ADDRESS SPECIFIC ##############################
    ############################################################################
    def get_balance_of_addr(self, address):
        """
        As is described in `validate_add_transaction()`, although most existing
        implementations involve Merkle Trees, this just does a manual search
        through all the transactions. There is little reason to believe that
        this cryptocurrency would ever cross a thousand transactions; for that
        reason alone I have not implemented Merkle Trees.

        Args:
            address (str): Address whose balance needs to be calculated

        Returns:
            tuple:
                Bool: The existence of the address
                float: Wallet balance (is 0.0 if address does not exist)
        """
        address = address.lower()
        flag_wallet_exists = False
        wallet_balance = 0.0

        # Go through blocks to check if address exists
        for block in self.chain:
            for transaction in block.transactions:

                # The address sent money, deduct value (amount + mining fees)
                if block.transactions[transaction]["sendr_addr"] == address:
                    wallet_balance -=                                          \
                        block.transactions[transaction]["value"]
                    flag_wallet_exists = True

                # The address received money, add amount (only amount)
                if block.transactions[transaction]["recvr_addr"] == address:
                    wallet_balance +=                                          \
                        block.transactions[transaction]["final_value"]
                    flag_wallet_exists = True

        # Go through transactions in TXPOOL if address exists
        for tx in self.TXPOOL:
             # The address sent money, deduct value (amount + mining fees)
            if self.TXPOOL[tx]["sendr_addr"] == address:
                wallet_balance -= self.TXPOOL[tx]["value"]
                flag_wallet_exists = True

            # The address received money, add amount (only amount)
            if self.TXPOOL[tx]["recvr_addr"] == address:
                wallet_balance += self.TXPOOL[tx]["final_value"]
                flag_wallet_exists = True

        return (flag_wallet_exists, wallet_balance)


    def get_transactions_of_addr(self, address):
        """
        Get all the transactions that an address is associated with address
        (including the transactions in TXPOOL)

        Args:
            address (str): Address whose transactions need to be found

        Returns:
            tuple:
                Bool : does the address exist
                dict : (a dictionary of dictionaries)
                    ```
                    {
                        "transaction_number" :
                        {
                            "type"        : "send" or "receive"
                            "in_txpool"   : True or False (is it in TXPOOL?)
                            "sendr_addr"  : sender address
                            "recvr_addr"  : receiver address
                            "value"       : total amount transacted
                            "mining_fee"  : mining fee
                            "final_value" : value - mining_fee
                            "skscript"    : signed message
                            "timestamp"   : timestamp
                        },
                        "transaction_number" : ...,
                        "transaction_number" : ...
                    }
                    ```
        """
        flag_address_exists = False
        transactions = {}
        tx_index = 0

        # Go through the blocks in the chain to check if any transactions
        # to/from this address were made
        for block in self.chain:
            for transaction in block.transactions:

                # The address sent money
                if block.transactions[transaction]["sendr_addr"] == address:
                    tx = deepcopy(block.transactions[transaction])
                    tx["type"] = "send"
                    tx["in_txpool"] = False

                    transactions[str(tx_index)] = tx
                    tx_index += 1

                    flag_address_exists = True

                # The address received money
                if block.transactions[transaction]["recvr_addr"] == address:
                    tx = deepcopy(block.transactions[transaction])
                    tx["type"] = "receive"
                    tx["in_txpool"] = False

                    transactions[str(tx_index)] = tx
                    tx_index += 1

                    flag_address_exists = True

        # Go through transactions in TXPOOL if any transactions to/from this
        # address were made
        for transaction in self.TXPOOL:

             # The address sent money
            if self.TXPOOL[transaction]["sendr_addr"] == address:
                tx = deepcopy(self.TXPOOL[transaction])
                tx["type"] = "send"
                tx["in_txpool"] = True

                transactions[str(tx_index)] = tx
                tx_index += 1

                flag_address_exists = True

            # The address received money
            if self.TXPOOL[transaction]["recvr_addr"] == address:
                tx = deepcopy(self.TXPOOL[transaction])
                tx["type"] = "receive"
                tx["in_txpool"] = True

                transactions[str(tx_index)] = tx
                tx_index += 1

                flag_address_exists = True

        return (flag_address_exists, transactions)


    ############################################################################
    ############################# ADD TRANSACTION ##############################
    ############################################################################
    def add_transaction(self, sendr_addr, recvr_addr, value, mining_fee,       \
        timestamp, skscript = None):
        """
        This is to be called right after `validate_add_transaction()`. This does
        not have any checks in bound and hence must be only called after a
        transaction parameters have been validated OR when the chain decides to
        create a genesis / pay mining fees / reward a transaction.

        Args:
            sendr_addr (str): sending address
            recvr_addr (str): receiving address
            value (int): amount being transferred
            mining_fee (float): mining fee for this transaction
            timestamp (str): timestamp of the transaction being first received
            skscript (str): signed script authorizing transaction

        NOTE:
            In the case of the chain creating a genesis / paying mining fee /
            rewarding a transaction, `skscript` is set to be the sender's
            address. For this, no argument has to be passed.

        Returns:
            Bool: Always returns `True` when successful
        """
        transaction = {
            "sendr_addr" : sendr_addr.lower(),
            "recvr_addr" : recvr_addr.lower(),
            "value" : value,
            "mining_fee" : mining_fee,
            "final_value" : value - mining_fee,
            "skscript" : skscript or sendr_addr,
            "timestamp" : timestamp
        }

        transaction["txhash"] = sha3_256(
            str(transaction).encode("utf-8")
        ).hexdigest()

        transaction_index = str(self.transaction_number)
        self.TXPOOL[transaction_index] = transaction
        self.transaction_number += 1

        return True


    def validate_add_transaction(self, incoming_tx, mining_fees):
        """
        Validates the transaction that is to be added and then adds the
        transaction to the blockchain.

        NOTE:
            This is actually supposed to be solved by Merkle Trees and the sorts
            and those are good for scaling up. As such, I do not believe that
            this (private) cryptocurrency will even have more than a thousand
            transactions. Thus, I believe that iterating through the chain is an
            okay solution for now. If this is ever updated to use merkle trees,
            *MAKE SURE* to update the `Block` class and almost every class
            method in this class.

            For reference: Ethereum has three merkle trees: state, transaction
            and receipt.
            (https://blog.ethereum.org/2015/11/15/merkling-in-ethereum/)

            Likewise, each block has to be updated too in order for it to comply
            with the new definition that is implemented. In other words, make
            sure to update each block stored as blocks.json before shifting over
            to a new spec of the chain.

        Args:
            incoming_tx (dict): the incoming transaction:
                ```
                {
                    "sendr_addr" (str) : sender address
                    "recvr_addr" (str) : receiver address
                    "value" (float)    : amount transferred (not including
                                         mining fees)
                    "skscript" (str)   : signature of transaction
                }
                ```

            mining_fees (float): mining fees that is required by the network to
                                 process this transaction

        Returns:
            (int):
                 1 : Transaction Successful
                -1 : Transaction Failed - Sender's address does not have enough
                                          funds to transfer value + mining fees
                -2 : Transaction Failed - Sender's address does not exist
                                          (subset of returning -1)
        """
        sendr_addr = incoming_tx["sendr_addr"].lower()
        recvr_addr = incoming_tx["recvr_addr"].lower()
        value = float(incoming_tx["value"])

        flag_sender_exists, sendr_wallet_balance = self.get_balance_of_addr(sendr_addr)

        # Sender does not exist
        if not flag_sender_exists:
            return -2

        # Sender does not have enough balance to send moneys
        if sendr_wallet_balance < (value + mining_fees):
            return -1

        self.add_transaction(sendr_addr, recvr_addr, value, mining_fees,
            time_utc(), skscript = incoming_tx["skscript"])

        return 1


    ############################################################################
    ########################### BLOCKCHAIN SPECIFIC ############################
    ############################################################################
    def get_complete_chain(self):
        """
        Get the entire blockchain. This does not include TXPOOL. Look at
        `get_txpool()` for getting TXPOOL

        Returns:
            dict: (a dictionary of dictionaries):
            ```
            {
                "block_index" :
                {
                    "block_index"         : block index
                    "mined_block_hash"    : the (mined) hash of this block. This
                                            is *NOT* equal to Block.block_hash
                    "previous_block_hash" : hash of the previous block
                    "nonce"               : nonce used to make hash meet
                                            difficulty
                    "difficulty"          : difficulty at the time the block was
                                            mined
                    "percent_tx_rewarded" : percentage of transactions rewarded
                    "mining_fee"          : mining fee of the block
                    "reward_for_tx"       : reward for rewarded transaction
                    "transactions"        :
                    {
                        "transaction_index" :
                        {
                            "sendr_addr"  : sender address
                            "recvr_addr"  : receiver address
                            "value"       : amount transacted
                            "mining_fee"  : mining fee for the transaction
                            "final_value" : value - mining_fee
                            "skscript"    : signed message from sender
                            "timestamp"   : timestamp of the transaction
                        },
                        "transaction_index" : ...,
                        "transaction_index" : ...,
                    }
                    "timestamp"           : timestamp the block was joined into
                                            the chain
                },
                "block_index" : ...,
                "block_index" : ...,
            }
            ```
        """
        complete_chain = {}
        block_files = [f for f in self.blocks_path.rglob("*.json")]

        for block_index, block_file in enumerate(block_files):
            with open(Path(block_file), 'r') as F:
                block_dict = load(F)
                complete_chain[str(block_index)] = block_dict

        return complete_chain


    def get_TXPOOL(self):
        """
        Gets all the transactions in the TXPOOL

        Returns:
            dict: (a dictionary of dictionaries)
                ```
                {
                    "transaction_number" :
                    {
                        "sendr_addr"  : sender address
                        "recvr_addr"  : receiver address
                        "value"       : value (total amount transacted)
                        "mining_fee"  : mining fee
                        "final_value" : value - mining_fee
                        "skscript"    : signed message
                        "timestamp"   : timestamp
                    }
                }
                ```
        """
        return self.TXPOOL


    ############################################################################
    ############################### LOAD CHAIN #################################
    ############################################################################
    def load_chain(self):
        """
        Go through `self.blocks_path` and read all the json block files and
        store them in chain.
        """
        # This assumes block_files has only *.json and nothing else
        # It can be made more rigourous, but eh.
        block_files = [f for f in self.blocks_path.rglob("*.json")]

        self.index = len(block_files)

        for block_file in block_files:
            with open(block_file, 'r') as F:
                block_dict = load(F)

                block = Block(
                    block_index = block_dict["block_index"],
                    mined_block_hash = block_dict["mined_block_hash"],
                    previous_block_hash = block_dict["previous_block_hash"],
                    nonce = block_dict["nonce"],
                    difficulty = block_dict["difficulty"],
                    transactions = block_dict["transactions"],
                    timestamp = block_dict["timestamp"]
                )

                self.chain.append(block)