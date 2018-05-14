# 启动两个节点（实例）
python blockchain.py -p 5000
python blockchain.py -p 5001

# 在 节点1（5000）上挖矿一次

# 在 节点2（5001）上挖矿两次

# 在 节点1（5000）上访问接口 /nodex/resolve，这时 节点1（5000）的区块链会通过共识算法被 节点2（5001）的链所替换