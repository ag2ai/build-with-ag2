import autogen
from autogen import LLMConfig
import re
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import requests
from bs4 import BeautifulSoup
import textwrap

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# code retrieved from https://stackoverflow.com/questions/79019497/retrieving-news-articles-from-yahoo-finance-canada-website
def getUuids(companyName):
    url = "https://ca.finance.yahoo.com/_finance_doubledown/api/resource?bkt=finance-CA-en-CA-def&device=desktop&ecma=modern"
    data = {
        "requests": {
            "g0": {
                "resource": "StreamService",
                "operation": "read",
                "params": {
                    "forceJpg": True,
                    "releasesParams": {"limit": 50, "offset": 0},
                    "ncpParams": {
                        "query": {
                            "id": "tickers-news-stream",
                            "version": "v1",
                            "namespace": "finance",
                            "listAlias": "finance-CA-en-CA-ticker-news",
                        }
                    },
                    "useNCP": True,
                    "batches": {
                        "pagination": True,
                        "size": 10,
                        "timeout": 1500,
                        "total": 170,
                    },
                    "category": f"YFINANCE:{companyName}",
                },
            }
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=data, headers=headers, verify=False).json()
    return resp["g0"]["data"]["stream_pagination"]["gqlVariables"]["tickerStream"][
        "pagination"
    ]["uuids"]


# llm_config = {"config_list": config_list, "timeout": 60}

llm_config = LLMConfig(
    api_type="openai",
    model="gpt-4o",
    cache_seed=42,
    temperature=0.1,
    timeout=60,
)

financial_assistant = autogen.AssistantAgent(
    name="financial_assistant",
    llm_config=llm_config,
)

research_assistant = autogen.AssistantAgent(
    name="research_assistant",
    llm_config=llm_config,
)

report_writer = autogen.AssistantAgent(
    name="report_writer",
    llm_config=llm_config,
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={
        "work_dir": "workspace",
        "use_docker": False,
    },
)


# code retrieved and modified from https://stackoverflow.com/questions/79019497/retrieving-news-articles-from-yahoo-finance-canada-website
@financial_assistant.register_for_llm(
    name="get_news_links", description="Get news links to a given company code."
)
@user_proxy.register_for_execution(name="get_news_links")
def get_news_links(companyCode: str) -> str:
    result = getUuids(companyCode)
    remove_junk = re.sub(":STORY|:VIDEO", "", result)
    result_url = f"https://ca.finance.yahoo.com/caas/content/article/?uuid={remove_junk}&appid=article2_csn"
    result_resp = requests.get(result_url, verify=False).json()

    all_links = ""
    max_news = 5
    for i in result_resp["items"]:
        try:
            news_modifiedDate = i["data"]["partnerData"]["modifiedDate"]
            if "2025" in news_modifiedDate:
                news_urls = i["data"]["partnerData"]["finalUrl"]
                news_title = i["data"]["partnerData"]["pageTitle"]
                all_links += f"News URL:  {news_urls}\nModifiedDate: {news_modifiedDate}\nTitle: {news_title}\n\n"
                max_news -= 1
        except Exception:
            pass
        if max_news == 0:
            break

    if all_links == "":
        return "No news found. The company code may be incorrect, or please use a different way to search for news."

    return all_links


@financial_assistant.register_for_llm(
    name="summarize_news", description="Summarize news from a given URL."
)
@user_proxy.register_for_execution(name="summarize_news")
def scrape_and_summarize_yahoo_finance(url: str, summary_length=1000) -> str:
    """
    Scrapes a Yahoo Finance article from the given URL and returns a summarized version.

    Parameters:
    - url (str): The URL of the Yahoo Finance article.
    - summary_length (int): The number of characters to include in the summary.

    Returns:
    - str: A summarized version of the article.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse the content using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract the article text
        article_paragraphs = soup.find_all("p")
        article_text = "\n".join([p.get_text() for p in article_paragraphs])

        # Summarize the content
        summary = textwrap.fill(article_text[:summary_length], width=80)
        return summary

    except requests.exceptions.RequestException as e:
        return f"Error fetching article: {e}"


async def main():

    # get user input
    stock_str = input("Enter the stock you want to investigate: ")

    financial_tasks = [
        f"Can you read recent news about {stock_str} stock? Retrieve the news links and get summaries for all news using functions.",
        f"Get the Monthly, 3 Months, YTD and one-year stock price change for {stock_str}. Plot a 1-year stock price change graph and save to `stock_price_change.png`.",
        "You are given recent news and price changes about a stock. please write a comprehensive market analysis report in markdown and give your conclusion on whether to hold, sell or buy it. Incorporating all findings, and include the plot `stock_price_change.png` from the previous task. Return the report in ```markdown``` format.",
    ]

    # Run the first two tasks asynchronously
    news_summary_task = user_proxy.a_initiate_chat(
        recipient=financial_assistant,
        message=financial_tasks[0],
        summary_method="reflection_with_llm",
        summary_args={
            "summary_prompt": "Please summaize the news content of the stock. Include details and url references to the news articles."
        },
    )
    price_change_task = user_proxy.a_initiate_chat(
        recipient=research_assistant,
        message=financial_tasks[1],
        summary_method="reflection_with_llm",
        summary_args={
            "summary_prompt": "Please give the requested stock price changes numbers and share your findings."
        },
    )

    # Gather the first two tasks and wait for their completion
    news_summary, price_change = await asyncio.gather(
        news_summary_task, price_change_task
    )

    user_proxy._code_execution_config = False
    report = await user_proxy.a_initiate_chat(
        recipient=report_writer,
        message=f"News summary: {news_summary.summary}\n\nStock price change: {price_change.summary}\n\n{financial_tasks[2]}",
        max_turns=1,
    )

    md_report = report.summary.split("```markdown")[1].split("```")[0]
    md_report.replace(
        "(stock_price_change.png)", "(./workspace/stock_price_change.png)"
    )
    with open("market_analysis_report.md", "w") as file:
        file.write(md_report)


if __name__ == "__main__":
    import asyncio

    chat_results = asyncio.run(main())
