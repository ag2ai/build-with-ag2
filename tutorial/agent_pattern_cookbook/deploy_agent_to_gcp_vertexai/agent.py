from autogen import ConversableAgent, LLMConfig
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

load_dotenv()

app = FastAPI()

Gemini_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure LLM
llm_config = LLMConfig(
    config_list={
        "model": "gemini-2.5-flash",
        "api_type": "google",
        "api_key": Gemini_API_KEY,
    }
)

# Initialize agent once (reusable)
assistant = ConversableAgent(
    "assistant",
    system_message="You are a helpful assistant",
    llm_config=llm_config,
    human_input_mode="TERMINATE",
)


class MessageRequest(BaseModel):
    message: str
    max_turn: int = 1


@app.get("/")
def health_check():
    return {"status": "healthy"}


@app.post("/chat")
def chat(request: MessageRequest):
    try:
        response = assistant.run(messages=request.message, max_turn=request.max_turn)
        result = response.process()
        return {"response": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
