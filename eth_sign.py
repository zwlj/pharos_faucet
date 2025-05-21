import sys
from eth_account import Account
from eth_account.messages import encode_defunct

def sign_message(private_key, message):
    """
    使用私钥对消息进行签名
    
    参数:
    private_key (str): 以太坊私钥，可以带有或不带有'0x'前缀
    message (str): 要签名的消息
    
    返回:
    str: 签名后的16进制字符串
    """
    # 确保私钥格式正确
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
        
    # 创建账户对象
    account = Account.from_key(private_key)
    
    # 编码消息
    encoded_message = encode_defunct(text=message)
    
    # 签名消息
    signed_message = account.sign_message(encoded_message)
    
    # 返回签名的16进制表示
    return signed_message.signature.hex()

def get_address_from_private_key(private_key):
    """
    从私钥获取对应的以太坊地址
    
    参数:
    private_key (str): 以太坊私钥，可以带有或不带有'0x'前缀
    
    返回:
    str: 对应的以太坊地址
    """
    # 确保私钥格式正确
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
        
    # 创建账户对象并返回地址
    account = Account.from_key(private_key)
    return account.address

def main():
    
    private_key = "测试私钥"
    message = "pharos"
    
    # 获取地址
    address = get_address_from_private_key(private_key)
    print(f"地址: {address}")
    
    # 签名消息
    signature = sign_message(private_key, message)
    print(f"消息: {message}")
    print(f"签名: {signature}")

if __name__ == "__main__":
    main()