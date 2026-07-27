import os
from openai import OpenAI


def load_env_file(path: str):
    """从 .env 文件加载键值到 os.environ（若系统环境变量已存在则不覆盖）。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(".env")

API_KEY = os.getenv("ARK_API_KEY", "").strip()
BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").strip()
PRIMARY_MODEL = os.getenv("ARK_MODEL", "doubao-1-5-lite-32k-250115").strip()


def candidate_models(primary: str):
    models = [
        primary,
        "doubao-1-5-lite-32k-250115",
        "doubao-1.5-lite-4k",
        "doubao-1-5-lite-4k",
    ]
    deduped = []
    for m in models:
        if m and m not in deduped:
            deduped.append(m)
    return deduped


def main():
    if not API_KEY:
        print("ARK_API_KEY 未配置，请先设置环境变量。")
        return
    print(f"API_KEY: {API_KEY}")
    print(f"Base URL: {BASE_URL}")
    print(f"Primary Model: {PRIMARY_MODEL}")
    print("开始连接方舟并测试候选模型...")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    last_error = None

    for model in candidate_models(PRIMARY_MODEL):
        try:
            print(f"\n尝试模型: {model}")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是人工智能助手。"},
                    {"role": "user", "content": "你好，请回复什么是质能方程。"},
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
            print(f"✅ 可用模型: {model}")
            print(f"回复内容: {content}")
            return
        except Exception as e:
            last_error = str(e)
            print(f"❌ 失败: {last_error}")

    print("\n所有候选模型都不可用。")
    if last_error:
        print(f"最后错误: {last_error}")


if __name__ == "__main__":
    main()
