from hashlib import sha3_256
from random import SystemRandom
from datetime import datetime


def time_utc():
    return str(datetime.utcnow())


def reward_tx(recvr_addr, reward, TXPOOL, sendr_addr = None):
    """
    Add a reward (essentially add a transaction to the blockchain)

    Args:
        recvr_addr (str): Receiver Address
        reward   (float): Amount to reward
        TXPOOL    (dict): Same as `mine()`'s arg of mine_params["TXPOOL"]
        sendr_addr (str): Sender's Address (default: "IceCereum-Rewards")
    """
    transaction = {
            "sendr_addr" : sendr_addr or "IceCereum-Rewards",
            "recvr_addr" : recvr_addr,
            "value" : reward,
            "mining_fee" : 0.0,
            "final_value" : reward,
            "skscript" : sendr_addr or "IceCereum-Rewards",
            "timestamp" : time_utc()
        }

    index = len(TXPOOL)

    transaction["txhash"] = sha3_256(
            str(transaction).encode("utf-8")
        ).hexdigest()

    TXPOOL[str(index)] = transaction


def mine(mine_params, miner_addr):
    """
        A very simple Proof-of-Work miner with a reward functionality. Explained
        in detail in docs/How-Coins-Are-Introduced.

        Args:
            mine_params (dict):
                {
                    "index"               : (int) index of the block that is
                                            going to be created
                    "prev_hash"           : (str) previous block hash
                    "difficulty"          : (int) difficulty
                    "mining_fees"         : (float) mining_fees
                    "reward_for_tx"       : (float) reward for tx
                    "percent_tx_rewarded" : (float) percentage of tx rewarded
                    "TXPOOL"              :
                        {
                            "tx_index" :
                                {
                                    "sendr_addr"  : (str) sender address
                                    "recvr_addr"  : (str) receiver address
                                    "value"       : (float) amount transacted
                                    "mining_fee"  : (float) mining fee
                                    "final_value" : (float) total amount
                                                    transacted after fee
                                    "skscript"    : (str) signed script
                                    "timestamp"   : (str) timestamp of t
                                },
                            "tx_index" : ...,
                            "tx_index" : ...,
                        }
                }
            miner_addr (str): miner address

        Returns:
            dict: same as mine_params["TXPOOL"] + rewarded transactions
            str : computed hash that meets the difficulty number
            str : the string value that succeeded in making the
                  hash(block_str + nonce) meet the difficulty
    """
    percent_tx_rewarded = float(mine_params["percent_tx_rewarded"])
    TXPOOL = mine_params["TXPOOL"]
    difficulty = int(mine_params["difficulty"])
    reward = float(mine_params["reward_for_tx"])

    num_transactions = len(TXPOOL)

    # The number of transactions that should be rewarded
    num_tx_rewarded = percent_tx_rewarded * num_transactions

    if num_tx_rewarded < 1:
        """
        If number of transactions that should be rewarded are less than one,
        generate a random number between [0,1). If this random number is less
        than the number of percent of transactions that should be rewarded, then
        reward one random transaction.

        Example:
            percent_tx_rewarded is 0.1 i.e., reward 10% of transactions. If
            number of transactions are 5, then num_tx_rewarded is 0.5. We now
            generate a random number; let it have turned out to be 0.07. Since
            this random number is less than percent_tx_rewarded (0.07 < 0.1),
            we reward one random transaction out of the 5 transactions.
        """
        if (SystemRandom().random() < percent_tx_rewarded):
            tx_num = SystemRandom().randint(0, num_transactions-1)

            reward_tx(recvr_addr = TXPOOL[str(tx_num)]["sendr_addr"],
                reward = reward, TXPOOL = TXPOOL)

    else:
        """
        The number of transactions that should be rewarded is greater than one.
        We now reward num_tx_rewarded random transactions.
        """
        rewarded_tx = [] # A list of all rewarded transactions

        num_tx_rewarded = int(num_tx_rewarded) # floor(num_tx_rewarded)

        while (len(rewarded_tx) <= num_tx_rewarded):
            tx_num = SystemRandom().randint(0, num_transactions-1)

            if tx_num not in rewarded_tx:
                rewarded_tx.append(tx_num)


        for tx_num in rewarded_tx:
            reward_tx(recvr_addr = TXPOOL[str(tx_num)]["sendr_addr"],
                reward = reward, TXPOOL = TXPOOL)

    # We now proceed to pay ourself (the miner)
    reward_tx(recvr_addr = miner_addr,
        reward = num_transactions * mine_params["mining_fees"], TXPOOL = TXPOOL,
        sendr_addr = "IceCereum-MiningPayment")

    # This is the string we need to concatenate the nonce to in order to meet
    # difficulty
    block_str = "{idx}{TXPOOL}{prev_hash}{diff}{mining_fees}{reward}{percent}" \
        .format(
            idx = mine_params["index"],
            TXPOOL = TXPOOL,
            prev_hash = mine_params["prev_hash"],
            diff = difficulty,
            mining_fees = mine_params["mining_fees"],
            reward = reward,
            percent = percent_tx_rewarded
        )

    nonce_int = 0

    while True:
        hash_string = sha3_256(
            bytes((block_str + hex(nonce_int)[2:]).encode("utf-8"))
        ).hexdigest()

        n_zeroes = len(hash_string) - len(hash_string.lstrip('0'))
        
        if n_zeroes == difficulty:
            break

        nonce_int += 1

    return (hash_string, hex(nonce_int)[2:], TXPOOL)

