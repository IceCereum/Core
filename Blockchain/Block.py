from hashlib import sha3_256
from datetime import datetime


def time_utc():
    return str(datetime.utcnow())


class Block:
    def __init__(self, block_index, mined_block_hash, previous_block_hash,
        nonce, difficulty, transactions, timestamp = None):
        """
        The `Block` constructor

        Args:
            block_index (int)         : block index
            mined_block_hash (str)    : the (mined) hash of this block. This is
                                        *NOT* equal to Block.block_hash
            previous_block_hash (str) : the hash of the previous block. This is
                                        *EQUAL TO* Block.block_hash
            nonce (str)               : the nonce required to make 
            difficulty (int)          : the difficulty at the time the block was
                                        created, used to calculate
                                        mined_block_hash
            transactions (dict)       : a dict of dictionaries of the form:
                ```
                "1" : {
                    "sendr_addr"  : sender's address
                    "recvr_addr"  : receiver's address
                    "value"       : total amount transacted
                    "mining_fee"  : mining fee for transaction
                    "final_value" : value - mining_fee
                    "skscript"    : signed script authorizing transaction
                    "timestamp"   : timestamp
                },
                "2" : ...,
                "3" : ...
                ```
            timestamp (str)           : datetime timestamp; if None, time_utc()
                                        is used
        """
        self.block_index = block_index
        self.previous_block_hash = previous_block_hash
        self.mined_block_hash = mined_block_hash
        self.nonce = nonce
        self.difficulty = difficulty
        self.transactions = transactions
        self.timestamp = timestamp or time_utc()


    @property
    def block_hash(self):
        block_str = \
            "|{index}|{block_hash}|{transactions}|{prev_block_hash}|{diff}" \
            "|{timestamp}|" \
            .format(
                index = self.block_index,
                block_hash = self.mined_block_hash,
                transactions = self.transactions,
                prev_block_hash = self.previous_block_hash,
                diff = self.difficulty,
                timestamp = self.timestamp
            )

        self._block_hash = \
            sha3_256(
                bytes(block_str.encode("utf-8"))
            ).hexdigest()

        return self._block_hash
