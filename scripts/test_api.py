import requests
import json

URL = "http://localhost:8000/api/execute"

def run_test(title, code, stdin=""):
    print(f"\n{'='*15} {title} {'='*15}")
    payload = {
        "code": code,
        "stdin": stdin
    }
    
    try:
        response = requests.post(URL, json=payload)
        
        # 打印 HTTP 状态码
        print(f"[*] HTTP Status: {response.status_code}")
        
        # 格式化输出 JSON 结果，确保中文正常显示
        if response.status_code == 200:
            res_json = response.json()
            print(json.dumps(res_json, indent=2, ensure_ascii=False))
        else:
            print(f"[!] 报错信息: {response.text}")
            
    except Exception as e:
        print(f"[!] 请求发生异常 (后端没启动或网络错误): {e}")

if __name__ == "__main__":
    # 测试 1：基础输出、中文、错误流分离
    run_test(
        "测试 1：正常输出 + 错误分离",
        "import sys\nprint('你好，这是正常输出！')\nprint('警告：这是错误输出', file=sys.stderr)"
    )

    # 测试 2：代码抛出异常
    run_test(
        "测试 2：代码异常捕获",
        "raise ValueError('我故意写错代码，测试报错栈')"
    )

    # 测试 3：stdin 交互
    run_test(
        "测试 3：stdin 输入",
        "name = input()\nprint(f'你好, {name}')",
        stdin="张三\n"
    )

    # 测试 4：死循环测试超时 (会卡住大概10秒左右)
    run_test(
        "测试 4：死循环超时",
        "print('开始死循环...')\nwhile True:\n    pass"
    )