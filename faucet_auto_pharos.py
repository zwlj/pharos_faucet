import json
import time
import threading
import concurrent.futures
from queue import Queue
from eth_sign import sign_message, get_address_from_private_key
import requests
from datetime import datetime


# 最大重试次数
MAX_RETRIES = 3
# 重试间隔（秒）
RETRY_DELAY = 1
# 线程数量
NUM_THREADS = 10
# 线程锁，用于同步写入日志文件
log_lock = threading.Lock()
# 线程锁，用于同步打印输出
print_lock = threading.Lock()
# 计数器锁
counter_lock = threading.Lock()

# 全局计数器
success_count = 0
fail_count = 0

# 读取eth_wallets.json文件
def read_wallet_keys(json_file_path):
    try:
        with open(json_file_path, 'r') as file:
            wallets = json.load(file)
            return wallets
    except Exception as e:
        print(f"读取钱包文件时出错: {e}")
        return []

# 安全打印，避免多线程打印混乱
def safe_print(message):
    with print_lock:
        print(message)

# 安全写入日志
def safe_log(message):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with log_lock:
        with open("log.txt", "a") as f:
            f.write(f"\n[{timestamp}] {message}")

# 登录
def login(address, signature):
    headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'authorization': 'Bearer null',
    # 'content-length': '0',
    'origin': 'https://testnet.pharosnetwork.xyz',
    'priority': 'u=1, i',
    'referer': 'https://testnet.pharosnetwork.xyz/',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    }

    params = {
        'address': address,
        'signature': '0x' + signature
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post('https://api.pharosnetwork.xyz/user/login', params=params, headers=headers, timeout=30)
            response.raise_for_status()  # 检查HTTP错误
            data = response.json()
            jwt = data['data']['jwt']
            return jwt
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                safe_print(f"登录请求失败 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
                safe_print(f"等待 {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                safe_print(f"登录请求失败，已达到最大重试次数: {e}")
                raise
        except (KeyError, ValueError) as e:
            safe_print(f"处理登录响应时出错: {e}")
            if response.text:
                safe_print(f"响应内容: {response.text}")
            raise

# 领取 faucet
def claim_faucet(jwt, address):
    headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'authorization': 'Bearer ' + jwt,
    # 'content-length': '0',
    'origin': 'https://testnet.pharosnetwork.xyz',
    'priority': 'u=1, i',
    'referer': 'https://testnet.pharosnetwork.xyz/',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    }

    params = {
        'address': address,
    }

    result = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post('https://api.pharosnetwork.xyz/faucet/daily', params=params, headers=headers, timeout=30)
            response.raise_for_status()  # 检查HTTP错误
            result = response.text
            safe_print(result)
            
            # 将钱包信息保存到文本文件
            safe_log(f"地址: {address}\n结果: {result}")
                
            return result
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                safe_print(f"领取水龙头请求失败 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
                safe_print(f"等待 {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                error_msg = f"领取水龙头请求失败，已达到最大重试次数: {e}"
                safe_print(error_msg)
                
                # 记录错误到日志文件
                safe_log(f"地址: {address}\n错误: {error_msg}")
                    
                return f"{{\"error\": \"{str(e)}\"}}"

# 处理单个钱包的函数
def process_wallet(wallet_data, index):
    global success_count, fail_count
    
    try:
        private_key = wallet_data["private_key"]
        address = wallet_data["address"]
        
        # 验证地址是否与私钥匹配
        derived_address = get_address_from_private_key(private_key)
        address_match = address.lower() == derived_address.lower()
        
        safe_print(f"\n钱包 #{index+1}:")
        safe_print(f"地址: {address} {'(已验证)' if address_match else '(不匹配!)'}")
        
        if not address_match:
            safe_print("跳过不匹配的钱包")
            with counter_lock:
                fail_count += 1
            return False
        
        # 签名消息
        try:
            message = "pharos"
            signature = sign_message(private_key, message)
            jwt = login(address, signature)
            result = claim_faucet(jwt, address)
            
            # 检查结果是否成功
            if result and '"code":0' in result:
                with counter_lock:
                    success_count += 1
                return True
            else:
                with counter_lock:
                    fail_count += 1
                return False
                
        except Exception as e:
            safe_print(f"处理钱包 {address} 时出错: {e}")
            with counter_lock:
                fail_count += 1
            
            # 记录错误到日志文件
            safe_log(f"地址: {address}\n处理错误: {str(e)}")
            return False
    except Exception as e:
        safe_print(f"处理钱包 #{index+1} 时发生未预期错误: {e}")
        with counter_lock:
            fail_count += 1
        return False

# 主函数
def main():
    global success_count, fail_count
    
    # 钱包文件路径
    wallet_file = "/Users/qianjue/project/pharos/eth_wallets.json"
    
    # 读取钱包数据
    wallets = read_wallet_keys(wallet_file)
    
    if not wallets:
        safe_print("没有找到钱包数据")
        return
    
    safe_print(f"找到 {len(wallets)} 个钱包")
    safe_print(f"将使用 {NUM_THREADS} 个线程并行处理")
    
    # 记录开始时间
    start_time = datetime.now()
    safe_log(f"\n\n=== 开始批量领取 (多线程) {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    # 重置计数器
    success_count = 0
    fail_count = 0
    
    # 使用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # 提交所有任务
        futures = {executor.submit(process_wallet, wallet, i): i for i, wallet in enumerate(wallets)}
        
        # 处理完成的任务
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            # 每完成10个任务显示进度
            if completed % 10 == 0 or completed == len(wallets):
                safe_print(f"进度: {completed}/{len(wallets)} ({completed/len(wallets)*100:.1f}%)")
    
    # 记录结束时间和统计信息
    end_time = datetime.now()
    duration = end_time - start_time
    summary = f"\n=== 批量领取完成 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
    summary += f"总计: {len(wallets)} 个钱包\n"
    summary += f"成功: {success_count} 个\n"
    summary += f"失败: {fail_count} 个\n"
    summary += f"耗时: {duration.total_seconds()/60:.2f} 分钟\n"
    summary += f"平均速度: {len(wallets)/(duration.total_seconds()/60):.2f} 个/分钟\n"
    
    safe_print(summary)
    safe_log(summary)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_print("\n程序被用户中断")
    except Exception as e:
        safe_print(f"\n程序执行过程中发生错误: {e}")
        # 记录全局错误到日志文件
        safe_log(f"全局错误: {str(e)}")