import sys
import flask
from flask import jsonify, request, make_response

sys.path.insert(0, "./")
from MiningNode.miner import *

MINING_ADDRESS = "0x0acc12cb5c4d8eb3d3bc6540176af2318031ad92"

app = flask.Flask(__name__)

@app.route("/mine-hash", methods=["POST"])
def mine_hash():
    """
    Runs the mining code

    Request (json):
        refer to `miner.mine()`'s argument `miner_params`

    Response (json):
        "hash_string"  : (str) the mined hash string
        "nonce"        : (str) the nonce used to meet difficulty
        "transactions" : (dict) refer to `miner.mine()`'s argument
                         `miner_params["transactions"]`. This contains rewarded
                         transactions & mining payment.
    """
    request_body = request.json

    hash_string, nonce, TXPOOL = mine(request_body, MINING_ADDRESS)

    response = {
        "hash_string" : hash_string,
        "nonce" : nonce,
        "transactions" : TXPOOL,
    }

    return make_response(jsonify(response), 200)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4501, threaded=False)