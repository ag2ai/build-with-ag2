from dotenv import load_dotenv
import os
from autogen import AssistantAgent, UserProxyAgent

load_dotenv()

# 配置 DeepSeek
config_list = [{
    "model": "deepseek-chat",
    "api_key": os.getenv("DEEPSEEK_API_KEY"),
    "base_url": os.getenv("DEEPSEEK_BASE_URL"),
}]

print("🤖 正在创建你的第一个 AI Agent...")

# 创建 AI 助手
assistant = AssistantAgent(
    "my_assistant",
    llm_config={"config_list": config_list},
    system_message="你是一个友好的助手。用简单易懂的语言回答问题。"
)

# 创建用户代理
user_proxy = UserProxyAgent(
    "user",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
    code_execution_config=False,
)

# 开始对话
print("Agent 已就绪！正在提问...\n")
user_proxy.initiate_chat(
    assistant,
    message="请用简单的语言解释：什么是 AI Agent？举一个生活中的例子。"
)
