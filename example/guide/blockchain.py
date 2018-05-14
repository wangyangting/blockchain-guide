import hashlib
import json
import time
from uuid import uuid4

import requests
from flask import Flask, jsonify, request
from urllib.parse import urlparse


class Blockchain:
    def __init__(self):
        self.chain = []  # 链
        self.current_transactions = []  # 当前的所有交易
        self.nodes = set()  # 节点列表

        # 构建创世区块
        self.new_block(previous_hash="1", proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        在区块链中创建一个新的区块
        :param proof: <int> 工作量证明算法给出的证明
        :param previous_hash: (Optional) <str> 前一个区块的 Hash 值
        :return: <dict> 新的区块
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'timestamp_date': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # 重置当前交易列表
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        创建一个新的交易，并将它加入到下一个待挖的区块中
        :param sender: <str> 发送者的地址
        :param recipient: <str> 接收者的地址
        :param amount: <int> 数量
        :return: <int> 保存该事务的区块的索引
        """

        self.current_transactions.append({
            'sender': sender,  # 发送者
            'recipient': recipient,  # 接收者
            'amount': amount,  # 数量
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        # 返回 chain 中最近的一个 Block（块）
        print("--> last_block: ", self.chain[-1])
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        通过 SHA-256 Hash 方式来哈希指定的区块
        :param block: <dict> 区块
        :return: <str> 区块的 SHA-256 Hash（哈希值）
        """

        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        校验工作量证明: 是否 hash(last_proof, proof) 以 4 个 0 开头
        :param last_proof: <int> 上一个块的证明
        :param proof: <int> 当前块的证明
        :return: <bool> 校验成功返回 True, 否则返回 False
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        print(f'推测的 Hash 是 : ', guess_hash, guess)
        return guess_hash[:4] == "0000"

    def proof_of_work(self, last_proof):
        """
        简单的工作量证明算法:
         - 找到一个数字 p', 使得 hash(pp') 以 4 个 0 开头
         - p 是上一个块的证明
         - p' 是当前块的证明
        :param last_proof: <int> 最新的证明
        :return: <int> 有效的证明
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        print("有效的 proof（证明）是: ", proof)
        return proof

    def register_node(self, address):
        """
        注册节点，添加一个新的节点到节点列表中
        :param address: <str> 节点地址. 例如. 'http://192.168.6.7:5000'
        :return: None
        """

        parse_url = urlparse(address)
        if parse_url.netloc:
            self.nodes.add(parse_url.netloc)
        elif parse_url.path:
            # 访问没有没有 scheme 的 url。例如，'192.168.0.5'
            self.nodes.add(parse_url.path)
        else:
            raise ValueError('无效的节点 URL')
        self.nodes.add(parse_url.netloc)

    def valid_chain(self, chain):
        """
        校验区块链，确定一个指定的区块链是否是有效的
        :param chain: <list> 一个区块链
        :return: 校验有效返回 True , 否则返回 False
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]  # 当前区块
            print("\n-----------\n", current_index)
            print(f'最新的区块是 : {last_block}')
            print(f'当前的区块是 : {block}')
            print("\n-----------\n")
            print("hash: ", block['previous_hash'], self.hash(last_block))
            print("proof: ", last_block['proof'], block['proof'], self.valid_proof(last_block['proof'], block['proof']))

            # 检查区块的 hash 是否正确
            if block['previous_hash'] != self.hash(last_block):
                return False

            # 检查工作量证明是否正确
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        这里是我们的共识算法，它主要用来解决多个节点区块链的冲突
        其方式是通过使用网络中最长的区块链来替换现有的链
        :return: <bool> 被替换返回 True, 否则返回 False
        """

        neighbours = self.nodes
        new_chain = None

        # 我们只寻找比我们更长的 chain
        max_length = len(self.chain)

        # 获取并验证来自网络中所有节点的区块链
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                print("response from node", node, length, max_length, chain)

                # 检测该区块链的长度和它本身是否有效
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # 如果我们发现一个新的（最长链）区块链，就用它来替换我们现有的区块链, 有效的区块链比我们现有的更长
        if new_chain:
            self.chain = new_chain
            return True

        return False


# 实例化节点
app = Flask(__name__)

# 为该节点生成一个全局唯一的地址，这里使用 uuid 来代替
node_identifier = str(uuid4()).replace('-', '')

# 实例化
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    """
    挖矿
    :return:
    """
    # 我们运行工作量算法的证明来获得下一个证明
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 给工作量证明的节点提供奖励
    # 发送者为 "0" 表示是新挖出的币
    blockchain.new_transaction(sender="0", recipient=node_identifier, amount=1)

    # 通过将其添加到链中来构建新的区块
    block = blockchain.new_block(proof)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    """
    新的交易
    :return:
    """
    values = request.get_json()

    # 检查 POST 请求中的字段
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # 创建新的交易
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'交易将会被添加到区块 {index}'}
    return jsonify(response), 201


@app.route('/node/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "错误: 请提供一个有效的节点列表", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': '新的节点已经被添加',
        'total_nodes': list(blockchain.nodes)
    }

    return jsonify(response), 201


@app.route('/test/node/register', methods=['POST'])
def test_register_nodes():
    values = request.get_json()
    print("test start register nodes:", values)

    response = {
        'message': 'Test New nodes have been added',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    """
    解决共识冲突
    :return:
    """
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': '我们的链已经被替换',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': '我们的链是最有权威的（最长链）',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='所需监听的端口')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)
