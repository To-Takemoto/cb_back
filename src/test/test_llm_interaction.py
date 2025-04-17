from ..infra.openrouter_client import OpenRouterLLMService
from ..usecase.llm_interaction import LLMInteractionUC
import asyncio

async def main():
    opnerouter_client = OpenRouterLLMService()
    intaraction_manageer = LLMInteractionUC(opnerouter_client)
    message = await intaraction_manageer.send_and_receive_message("こんにちは")
    print(message)

asyncio.run(main())
#uv run -m src.test.test_llm_interaction