import io
import logging
from typing import Optional
from src.models import InvoiceData
from PIL import Image
from pydantic_ai import Agent, AgentRunResult, BinaryImage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

logger = logging.getLogger('ExtractionAgent')

class ExtractionAgent:

    def _get_model(self, model_name: str, api_key: str, base_url: Optional[str]=None) -> OpenAIChatModel:
        # initialize the provider
        provider = OpenAIProvider(base_url=base_url, # None for standard OpenAI since this is defaulted
                                  api_key=api_key)

        # initialize the model
        model = OpenAIChatModel(model_name=model_name, provider=provider)
        return model

    def __init__(self, model_name: str, api_key: str, base_url: Optional[str] = None):
        model = self._get_model(model_name=model_name, api_key=api_key, base_url=base_url)

        # set up the agent
        self.agent = Agent(
            model=model,
            instrument=True, # enables use of logfire when wanted
            name="ExtractionAgent",
            retries=2,
            output_retries=2
        )

        # we use instructions > system prompt to follow Pydantic AI best practices. Ensuring cleaner prompt scoping that
        # would prevent prompt redundancy if the system would expand to multi-turn/agentic.
        # See: https://ai.pydantic.dev/agent/#instructions
        self.agent.instructions(self._core_persona)

    def _core_persona(self) -> str:
        return (
            "Role: Senior Financial Audit Specialist & Data Extraction Expert.\n\n"
            
            "Context:\n"
            "You are processing international invoices. Your goal is to digitize "
            "financial documents with 100% integrity.\n\n"
            
            "Instructions:\n"
            "1. Literal Extraction: Retrieve all values exactly as they appear. Do not apply rounding, normalization, "
            "or mathematical corrections. If the document contains an error, the error must be preserved in the extraction.\n"
            "2. Spatial Logic: Use the visual layout to map concepts. Associate line items with their respective prices "
            "& identify seller/vendor information based on header alignment and proximity. \n"
            "3. Date Interpretation: Use document context (vendor information, language) to correctly interpret the "
            "date format in the document: Date-Month-Year vs Month-Date-Year.\n"
            "4. Zero Hallucination: return None for fields not present in the document.\n"
            "5. Semantic Classification: Infer the expense category by analyzing the vendor identity and line item descriptions.\n"
            "6. Currency Extraction: Extract the currency if explicitly mentioned. Do not infer or assume currency "
            "based on vendor location or other context. Currency symbols are typically found next to the total amount.\n\n"
            
            "Constraint:\n"
            "- Return ONLY structured data matching the provided schema.\n"
            "- Do not include any explanatory text, reasoning steps, or formatting outside of the structured data.\n"
        )

    async def extract_data(self, image: Image.Image) -> AgentRunResult:
        """
        Extracts structured data from an invoice image. It first converts the image to bytes and then sends it to the
        agent extract the relevant information according to the InvoiceData schema.

        :param image: Image of the invoice to be processed
        :return: Structured data extracted from the invoice, adhering strictly to the InvoiceData schema.
        """
        # initialize the buffer
        buffer = io.BytesIO()

        # set optimize to True and quality to 95 to reduce file size while maintaining quality, even though this will
        # not save API costs as this is based on dimensions, it is beneficial for API latency.
        image.save(buffer, format='JPEG', quality=95, optimize=True)
        image_bytes = buffer.getvalue()

        prompt = (
            "Extract the structured data from the provided invoice."
        )

        return await self.agent.run(
            [prompt, BinaryImage(data=image_bytes, media_type='image/jpeg')],
            output_type=InvoiceData,
            model_settings={'openai_reasoning_effort': 'low'},  # set reasoning effort to low dict gets ignored by non-OpenAI models
        )





