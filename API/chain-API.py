import os, sys, json
from uuid import uuid4
from functools import wraps
from datetime import timedelta 
from requests import post

import eth_utils
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

import flask
from flask import jsonify, request, session, abort, make_response

sys.path.insert(0, "./")
from Blockchain.Chain import Cryptocurrency

app = flask.Flask(__name__)

# Generate this by: running `python3 -c 'import os; print(os.urandom(16))'`
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/' # <-- This is the flask default key

# Global Cryptocurrency instance
Crypto = None


def is_local(function):
    """
    This is to check whether the call is being made from a controlled source or
    from outside. Since this is a private blockchain and a pretty simplfied
    version too, we're just going to let a few blockchain calls that create a
    block, create genesis, load the chain and mine a block only be called by an
    external control - either me or a cron job.

    To make use of this method, type `export COINSECRET="coinsecret"` in the
    terminal that this program is launched in. Every request that requires the
    use of this check has to have `"secret" : "coinsecret"` as a field in the
    request.

    NOTE:
        This is not related to `app.secret_key`. That is used for maintaining
        history between independent HTTP calls.
    """
    @wraps(function)
    def is_local_check(*args, **kwargs):
        request_body = request.json
        try:
            if request_body["secret"] != os.environ["COINSECRET"]:
                raise Exception
        except:
            abort(401)

        return function(*args, **kwargs)
    return is_local_check


@app.route("/create-genesis", methods=['GET'])
@is_local
def create_genesis():
    """
    This is to be run only once at the beginning of the blockchain. It
    immediately creates the 0th block.

    Request Args:
        secret (str)  : The os.environ["COINSECRET"] value
        address (str) : The address to send the genesis coins to
        amount (float): The amount of coins to send

    Response (json):
        success : (bool) Request success

    cURL command:
        curl -H "Content-Type: application/json" -X GET -d \
            '{"secret":"SECRET", "address":"0x....", "amount":10000.0}' \
            http://127.0.0.1:4500/create-genesis
    """
    try:
        address = request.json["address"]
        amount = float(request.json["amount"])
    except:
        return json.dumps({'success':False}), 200,                              \
            {'ContentType':'application/json'}
        
    global Crypto
    Crypto = Cryptocurrency(create_genesis = True, address = address, 
        amount = amount)

    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}


@app.route("/load-chain", methods=["GET"])
@is_local
def load_chain():
    """
    This is run if the API program was terminated and the previous state of the
    blockchain is required to be loaded.

    Request Args:
        secret (str): The os.environ["COINSECRET"] value

    Response (json):
        success : (bool) Request success

    cURL command:
        curl -H "Content-Type: application/json" -X GET -d \
            '{"secret":"SECRET"}' http://127.0.0.1:4500/load-chain
    """
    global Crypto
    Crypto = Cryptocurrency()

    Crypto.load_chain()

    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}


################################################################################
############################## PUBLIC METAROUTES ###############################
################################################################################
@app.route("/get-metaparameters", methods=["GET"])
def get_metaparameters():
    """
    Get the current metaparameters of the blockchain

    Response (json):
        "index"               : (int) index of the block that this TXPOOL will
                                become
        "prev_hash"           : (str) hash of the previous block
        "difficulty"          : (int) difficulty
        "mining_fees"         : (float) mining fees per transaction
        "num_tx_TXPOOL"       : (int) number of transactions in TXPOOL
        "reward_for_tx"       : (float) reward for rewarded transaction
        "percent_tx_rewarded" : (float) percentage of transactions rewarded

    cURL command:
        curl -H "Content-Type: application/json" -X GET \
            http://127.0.0.1:4500/get-metaparameters
    """
    metaparams = Crypto.get_latest_block_metaparams()
    
    response = {
        "index" : metaparams["index"],
        "prev_hash" : metaparams["prev_hash"],
        "difficulty" : metaparams["difficulty"],
        "mining_fees" : metaparams["mining_fees"],
        "num_tx_TXPOOL" : metaparams["num_tx_TXPOOL"],
        "reward_for_tx" : metaparams["reward_for_tx"],
        "percent_tx_rewarded" : metaparams["percent_tx_rewarded"]
    }

    return make_response(jsonify(response), 200)


@app.route("/get-txpool", methods=["GET"])
def get_txpool():
    """
    Get all the transactions in the current TXPOOL

    Response (json of json objects):
        "transaction_index" :
        {
            "sendr_addr"  : (str) sender address
            "recvr_addr"  : (str) receiver address
            "value"       : (float) amount transacted
            "mining_fee"  : (float) mining fees
            "final_value" : (float) value - mining_fee
            "skscript"    : (str) signature of transaction
            "timestamp"   : (str) datetime timestamp (datetime.now())
        },
        "transaction_index" : ...,
        "transaction_index" : ...,

    cURL command:
        curl -H "Content-Type: application/json" -X GET \
            http://127.0.0.1:4500/get-txpool
    """
    response = Crypto.get_TXPOOL()
    return make_response(jsonify(response), 200)


@app.route("/get-complete-chain", methods=["GET"])
def get_complete_chain():
    """
    Get the entire chain and all transactions excluding transactions in TXPOOL

    Response (json of json objects):
        "block_index" :
        {
            "block_index"         : (int) block_index
            "mined_block_hash"    : (str) the (mined) hash of that block *NOT*
                                    equal to block.block_hash
            "previous_block_hash" : (str) hash of the prev block
            "nonce"               : (str) nonce used to make hash meet
                                    difficulty
            "difficulty"          : (int) difficulty at the time the block was 
                                    mined
            "transactions" :
                {
                    "transaction_index" :
                        {
                            "sendr_addr"  : (str) sender address
                            "recvr_addr"  : (str) receiver address
                            "value"       : (float) amount transacted
                            "mining_fee"  : (float) mining fee for the tx
                            "final_value" : (float) value - mining_fee
                            "skscript"    : (str) signed message from sender
                            "timestamp"   : (str) timestamp of tx
                        },
                    "transaction_index" : ...,
                    "transaction_index" : ...,
                }
            "timestamp" : (str) timestamp the block was joined into the chain
        },
        "block_index" : ...,
        "block_index" : ...,

    cURL command:
        curl -H "Content-Type: application/json" -X GET \
            http://127.0.0.1:4500/get-complete-chain
    """
    response = Crypto.get_complete_chain()
    return (make_response(jsonify(response)), 200)


################################################################################
############################ PUBLIC PRIVATE-ROUTES #############################
################################################################################
@app.route("/get-balance", methods=["GET"])
def get_balance():
    """
    Get balance of an address

    Request (json):
        "sendr_addr" : (str) address to get the balance of

    Response (json):
        "message" : (str) Message
        "balance" : (float) Balance
        "exists"  : (bool) Account Existence
        "success" : (bool) Success

    Possible Messages:
        "sendr_addr NOT FOUND IN REQUEST" : The request json did not have
                                            sendr_addr
        "SENDER ADDRESS DOES NOT EXIST"   : The sender address does not exist on
                                            the blockchain
        "SENDER ADDRESS FOUND"            : The sender address exists on the
                                            blockchain and the values are part
                                            of the response

    cURL command:
        curl -H "Content-Type: application/json" -X GET -d \
            '{"sendr_addr":"0x...."}' http://127.0.0.1:4500/get-balance
    """
    def gen_response(msg, bal, exst, succ):
        response = {
            "message" : msg,
            "balance" : bal,
            "exists"  : exst,
            "success" : succ
        }
        return response

    address = None
    try:
        address = request.json["sendr_addr"]
    except:
        message = "sendr_addr NOT FOUND IN REQUEST"
        response = gen_response(message, -1.0, False, False)

        return make_response(jsonify(response), 200)


    exists, balance = Crypto.get_balance_of_addr(address)

    if not exists:
        message = "SENDER ADDRESS DOES NOT EXIST"
        response = gen_response(message, 0.0, False, True)

        return make_response(jsonify(response), 200)

    message = "SENDER ADDRESS FOUND"
    response = gen_response(message, balance, True, True)

    return make_response(jsonify(response), 200)


@app.route("/get-transactions", methods=["GET"])
def get_transactions():
    """
    Get transactions of an address

    Request (json):
        "sendr_addr" : (str) address to get the transactions of

    Response (json):
        "message"      : (str) Message
        "exists"       : (bool) Account Existence
        "success"      : (bool) Success
        "transactions" : (json object)
            {
                "transaction_number" :
                {
                    "type"        : (str) "send" or "receive"
                    "in_txpool"   : (Bool) True or False (is it in TXPOOL?)
                    "sendr_addr"  : (str) sender address
                    "recvr_addr"  : (str) receiver address
                    "value"       : (float) total amount transacted
                    "mining_fee"  : (float) mining fee
                    "final_value" : (float) value - mining_fee
                    "skscript"    : (str) signed message
                    "timestamp"   : (str) datetime timestamp (datetime.now())
                },
                "transaction_number" : ...,
                "transaction_number" : ...,
            }


    Possible Messages:
        "address NOT FOUND IN REQUEST" : The request json did not have address
        "ADDRESS DOES NOT EXIST"       : The address does not exist on the
                                         blockchain
        "ADDRESS FOUND"                : The address exists on the blockchain
                                         and the values are part of the response

    cURL command:
        curl -H "Content-Type: application/json" -X GET -d \
            '{"address":"0x...."}' http://127.0.0.1:4500/get-transactions
    """
    def gen_response(msg, exst, succ, tx):
        response = {
            "message"      : msg,
            "exists"       : exst,
            "success"      : succ,
            "transactions" : tx
        }
        return response

    address = None
    try:
        address = request.json["address"]
    except:
        message = "address NOT FOUND IN REQUEST"
        response = gen_response(message, False, False, {})

        return make_response(jsonify(response), 200)

    exists, transactions = Crypto.get_transactions_of_addr(address)

    if not exists:
        message = "ADDRESS DOES NOT EXIST"
        response = gen_response(message, False, True, {})

        return make_response(jsonify(response), 200)

    message = "ADDRESS FOUND"
    response = gen_response(message, True, True, transactions)

    return make_response(jsonify(response), 200)


################################################################################
###################### ERROR HANDLER FOR add_transaction #######################
################################################################################
def error_desc_add_transaction(errno, **kwargs):
    """
    This is a set of errors that can happen during add_transaction. Each error
    has a number and an associated error message, request success and status.
    For a descriptive definition of each error message, read the docstring of
    add_transaction

    Args:
        errno (int) : the error number

    Keyword Arguments:
        identifiers : (str) identifiers missing in the session cookies
        fields      : (str) fields in the request json

    Returns:
        make_response(jsonify({"message":..., "success":...}), HTTP status)
    """
    errors = {
        1 : {
                "error_desc" : {
                    "message" : "sendr_addr NOT FOUND IN REQUEST",
                    "success" : False
                    },
                "status" : 200
            },
        2 : {
                "error_desc" : {
                    "message" : "MISSING SESSION IDENTIFIER: {}".              \
                        format(kwargs.get("identifiers")),
                    "success" : False
                    },
                "status" : 200
            },
        3 : {
                "error_desc" : {
                    "message" : "MISSING {} FIELDS".                           \
                        format(kwargs.get("fields")),
                    "success" : False
                    },
                "status" : 200
            },
        4 : {
                "error_desc" : {
                    "message" : "SIGNATURE VALIDTION ERROR - UNEXPECTED "      \
                                "RECOVERABLE SIGNATURE LENGTH",
                    "success" : False
                    },
                "status" : 200
            },
        5 : {
                "error_desc" : {
                    "message" : "SIGNATURE VALIDTION ERROR - SIGNATURES DO "   \
                                "NOT MATCH",
                    "success" : False
                    },
                "status" : 200
            },
        6 : {
                "error_desc" : {
                    "message" : "INSUFFICIENT FUNDS",
                    "success" : False
                    },
                "status" : 200
            },
        7 : {
                "error_desc" : {
                    "message" : "SENDER ADDRESS DOES NOT EXIST",
                    "success" : False
                    },
                "status" : 200
            },
        8 : {
                "error_desc" : {
                    "message" : "SENDER ADDRESS NOT VALID",
                    "success" : False
                },
                "status" : 200
        },
        9 : {
                "error_desc" : {
                    "message" : "RECVR ADDRESS NOT VALID",
                    "success" : False
                },
                "status" : 200
        }
    }

    return make_response(
        jsonify(errors[errno]["error_desc"]), errors[errno]["status"])


################################################################################
############################### ADD TRANSACTION ################################
################################################################################
@app.route("/transfer-funds", methods=["GET", "POST"])
def add_transaction():
    """
    Add a transaction to the txpool

    Protocol:
        1. Client initiates via GET json({'sendr_addr':sender_address})

        2. (Internal)
            2.1 Generate one_time_nonce
            2.2 Set session cookies "identifier" : sender_address and
                "one_time_nonce" : one_time_nonce

        3. Send response json({"one_time_nonce":one_time_nonce})

        4. Client replies with POST json(check Request (of POST)). This expires
           after 5 minutes

        5. Authenticate Signed Message:
            5.1 message_to_sign = "{sendr_addr}{recvr_addr}{value}{nonce}"
            5.2 address = recover_message(message_to_sign, skscript)

        6. Validate Sender's Address

    Request (of GET):
        "sendr_addr" (str) : sender address

    Response (of GET):
        "message" : (str) message,
        "mining_fees" : (float) mining_fees,
        "one_time_nonce" : (str) one_time_nonce,
        "success" : (Bool) True

        If success if false, these are the possible error messages:
            "sendr_addr NOT FOUND IN REQUEST" : Missing sendr_addr in the
                                                request GET JSON

    Request (of POST):
        "sendr_addr"     : (str) sender address
        "recvr_addr"     : (str) receiver address
        "value"          : (float) amount being transferred
        "one_time_nonce" : (str) one time nonce generated during GET
        "skscript"       : (str) signed message to authenticate

    Response (of POST):
        "message" : (str) message
        "success" : (Bool) success

        If success if false, these are the possible error messages:
            "MISSING SESSION IDENTIFIER: {} : Missing the session identifier
                                              that is used to identify HTTP
                                              sessions

            "MISSING {} FIELDS" : Missing {} fields in the request POST JSON

            "SIGNATURE VALIDTION ERROR - " :
                - "UNEXPECTED RECOVERABLE SIGNATURE LENGTH" :
                    - This indicates that the signature length (len(skscript))
                        did not equal 65 bytes
                - "SIGNATURES DO NOT MATCH" :
                    - This indicates that the message was not signed by the
                        sender account. Possible forgery!

            "INSUFFICIENT FUNDS" : Insufficient funds in the sender's wallet

            "SENDER ADDRESS DOES NOT EXIST" : Sender's Address does not exist.
                                              This is a subset of
                                              "INSUFFICIENT FUNDS"

            "TRANSACTION SUCCESSFULLY ADDED TO TXPOOL" : Transaction verified
    """

    ########################
    ### GET BEGINS HERE ####
    ########################
    if request.method == "GET":
        # The session is only valid for 5 minutes, after which the session
        # identifiers expire
        session.permanent = True
        app.permanent_session_lifetime = timedelta(minutes=5)

        try:
            session['identifier'] = request.json["sendr_addr"]
        except:
            return error_desc_add_transaction(1)

        mining_fees = Crypto.get_latest_block_metaparams()["mining_fees"]

        one_time_nonce = str(uuid4().hex)
        response = {
            "message" : "SUCCESS",
            "mining_fees" : mining_fees,
            "one_time_nonce" : one_time_nonce,
            "success" : True
        }

        session["one_time_nonce"] = one_time_nonce

        return make_response(jsonify(response), 200)

        ########################
        #### GET ENDS HERE #####
        ########################

    elif request.method != "POST":
        abort(405)

    ########################
    ### POST BEGINS HERE ###
    ########################
    MINING_FEES = Crypto.get_latest_block_metaparams()["mining_fees"]

    if "identifier" not in session:
        return error_desc_add_transaction(2, identifiers="identifier")

    if "one_time_nonce" not in session:
        return error_desc_add_transaction(2, identifiers="one_time_nonce")

    request_body = request.json

    keys = ["sendr_addr", "recvr_addr", "value", "one_time_nonce", "skscript",
            "skscript_nonce"]
    missing_keys = []
    for key in keys:
            if key not in request_body:
                missing_keys.append(key)

    if len(missing_keys) > 0:
        return error_desc_add_transaction(3, fields=" ".join(missing_keys))

    if not Web3().isAddress(request_body["sendr_addr"]):
        return error_desc_add_transaction(8)
    if not Web3().isAddress(request_body["recvr_addr"]):
        return error_desc_add_transaction(9)

    ###########################
    ### BEGIN SKSCRIPT AUTH ###
    ###########################
    message_to_sign = "{sendr_addr}{recvr_addr}{value}{nonce}"                 \
        .format(
            sendr_addr = request_body["sendr_addr"],
            recvr_addr = request_body["recvr_addr"],
            value = request_body["value"],
            nonce = session["one_time_nonce"]
        )
    msg = encode_defunct(text = message_to_sign)


    try:
        signature = request_body["skscript_nonce"]
        validate_acct =                                                        \
            Account.recover_message(msg, signature = signature)
        validate_acct = validate_acct.lstrip(" ").rstrip(" ").lower()
    except eth_utils.exceptions.ValidationError:
        return error_desc_add_transaction(4)

    if request_body["sendr_addr"] != validate_acct:
        # this is trying to spend on someone else
        return error_desc_add_transaction(5)

    # At this point, every thing has been (hopefully...) validated
    # cryptographically. The next thing to do is check funds and balances which
    # validate_add_transaction does. This also adds the transaction to the
    # blockchain
    transaction_added = Crypto.validate_add_transaction(
                incoming_tx = request_body,
                mining_fees = MINING_FEES,
            )

    if transaction_added == -1:
        return error_desc_add_transaction(6)

    if transaction_added == -2:
        return error_desc_add_transaction(7)

    if transaction_added ==  1:
        response = {
            "message" : "TRANSACTION SUCCESSFULLY ADDED TO TXPOOL",
            "success" : True
        }
        return make_response(jsonify(response), 200)


################################################################################
############################### MINE THE BLOCK #################################
################################################################################
def create_block(mined_block_hash, nonce):
    """
    Creates a block on the blockchain

    Args:
        mined_block_hash (str): the (mined) hash of the block (submitted by the
                                miner)
        nonce (str)           : the nonce used to meet difficulty

    Returns:
        tuple:
            int : status of creating block
            dict:
                ```
                {
                    "message" : (str) message
                    "success" : (Bool) success
                }
                ```

    Possible Messages:
        "ERROR CREATING BLOCK" : There was something that went wrong when
                                 creating the block
        "BLOCK CREATED"        : The block was created
    """

    try:
        Crypto.create_block(mined_block_hash = mined_block_hash, nonce = nonce)
    except:
        response = {
            "message" : "ERROR CREATING BLOCK",
            "success" : False
        }
        return (-1, response)

    response = {
        "message" : "BLOCK CREATED",
        "success" : True
    }
    return (1, response)


@app.route("/mine-block", methods=["GET"])
@is_local
def mine_block():
    """
    Convert the TXPOOL into a block on the blockchain

    Protocol:
        1. GET /mine-block
        2. POST to mining pool super node (here: localhost:4501/mine-hash).
           POST JSON is Crypto.get_latest_block_metaparams().
        3. POST response contains hash_string, nonce, transactions.

    Response (json):
        "message" : (str) message
        "success" : (Bool) success

    Possible Messages:
        "ERROR CREATING BLOCK" : There was something that went wrong when
                                 creating the block
        "BLOCK CREATED"        : The block was created
    """
    POST_data = Crypto.get_latest_block_metaparams()

    # Notify miners (listening on 4501) about new challenge
    mining_resp = post("http://127.0.0.1:4501/mine-hash", json = POST_data)
    mining_resp = mining_resp.json()

    # Modify Crypto's TXPOOL with mining_response's TXPOOL (because it rewarded
    # some senders & added mining fee). This isn't really a great way to do
    # things, but since this has been created with a lot of liberties I think
    # it's fine.
    Crypto.TXPOOL = mining_resp["transactions"]

    # We now create the block on the blockchain. This also does assume that 
    # the miners *do*, in fact, reply and not just ghost us for whatever reason.
    stat, message = create_block(mined_block_hash = mining_resp["hash_string"],
            nonce = mining_resp["nonce"])

    return make_response(jsonify(message), 200)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4500, threaded=False)