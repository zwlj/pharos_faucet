import os
import json
from eth_account import Account
import secrets
import binascii

# 启用生成助记词的功能
Account.enable_unaudited_hdwallet_features()

# 生成钱包的数量
NUM_WALLETS = 10000  # 您可以根据需要修改这个数字

# 输出文件名
OUTPUT_FILE = "eth_wallets.txt"
OUTPUT_JSON = "eth_wallets.json"

# 存储所有钱包信息的列表
wallets = []

def generate_wallet():
    # 直接使用Account.create()创建新账户
    account = Account.create()
    
    # 获取私钥（十六进制字符串，不带0x前缀）
    private_key = account.key.hex()  # 移除'0x'前缀
    
    # 获取地址
    address = account.address
    
    # 生成助记词
    # 使用Account内置的方法创建带有助记词的账户
    mnemonic_account = Account.create_with_mnemonic()
    mnemonic = mnemonic_account[1]  # 获取助记词
    
    return {
        "private_key": private_key,
        "address": address,
        "mnemonic": mnemonic
    }

# 批量生成钱包
for i in range(NUM_WALLETS):
    wallet = generate_wallet()
    wallets.append(wallet)
    print(f"生成钱包 #{i+1}: {wallet['address']}")

# 将钱包信息保存到文本文件
with open(OUTPUT_FILE, "w") as f:
    f.write(f"生成了 {NUM_WALLETS} 个以太坊钱包\n\n")
    for i, wallet in enumerate(wallets):
        f.write(f"钱包 #{i+1}:\n")
        f.write(f"地址: {wallet['address']}\n")
        f.write(f"私钥: {wallet['private_key']}\n")
        f.write(f"助记词: {wallet['mnemonic']}\n\n")

# 将钱包信息保存到JSON文件
with open(OUTPUT_JSON, "w") as f:
    json.dump(wallets, f, indent=4)

print(f"\n钱包信息已保存到 {OUTPUT_FILE} 和 {OUTPUT_JSON}")