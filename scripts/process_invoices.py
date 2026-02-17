import os
import dotenv
import logging
import asyncio
from pathlib import Path
from src.extraction_agent import ExtractionAgent
from src.utils import load_document

dotenv.load_dotenv()
logger = logging.getLogger('ProcessInvoices - Script')

if os.getenv('LOGFIRE_TOKEN'):
    import logfire
    logfire.configure()
    logfire.instrument_pydantic_ai()

async def process_invoice(file_path: Path, agent: ExtractionAgent):
    try:
        file_extension = os.path.splitext(file_path)[-1].lower()
        file_byes = file_path.read_bytes()
        document_image = load_document(file_bytes=file_byes, extension=file_extension)

        invoice_data = await agent.extract_data(image=document_image)
        logger.info(f"Extracted data for file {file_path}: {invoice_data.output}")
        return invoice_data.output


    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


if __name__ == "__main__":
    # initialize the agent and logger
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    agent = ExtractionAgent(model_name=os.getenv('MODEL_NAME'), api_key=os.getenv('OPENAI_API_KEY'))

    data_dir = Path('data')

    # process the files
    for file_path in data_dir.iterdir():
        logger.info(f'Processing file: {file_path}')
        extracted_invoice = asyncio.run(process_invoice(file_path=file_path, agent=agent))
        break










