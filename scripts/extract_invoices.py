import os
import dotenv
import logging
import asyncio
import json
from pathlib import Path
from src.extraction_agent import ExtractionAgent
from src.models import InvoiceData
from src.utils import load_document, gather_with_concurrency

dotenv.load_dotenv()
logger = logging.getLogger('ExtractInvoices - Script')

# initialise logfire if the token is provided
if os.getenv('LOGFIRE_TOKEN'):
    import logfire
    logfire.configure()
    logfire.instrument_pydantic_ai()

async def process_invoice(file_path: Path, agent: ExtractionAgent) -> InvoiceData:
    """
    Process a single invoice document, extracting data using the provided agent.

    :param file_path: file path to the invoice document
    :param agent: agent instance to use for data extraction
    :return: extracted invoice data or None if an error occurs
    """
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


async def main(agent: ExtractionAgent, data_dir: Path, concurrent_tasks: int = 5):
    """
    Main function to process all invoice documents in the specified directory using the provided agent in parallel with
    limited concurrency. saves the extracted data in a JSON file "extracted_invoices.json".

    :param agent: agent instance to use for data extraction
    :param data_dir: directory containing invoice documents to be processed
    :param concurrent_tasks: number of concurrent tasks to run when processing invoices, default is 5 to balance speed and model load
    :return:
    """
    # Create tasks for all files
    tasks = []
    file_paths = []
    for file_path in data_dir.iterdir():
        logger.info(f'Processing file: {file_path}')
        tasks.append(process_invoice(file_path=file_path, agent=agent))
        file_paths.append(file_path)

    # Process with limited concurrency 5 at a time to avoid overwhelming the model but speed up throughput
    extracted_invoices = await gather_with_concurrency(concurrent_tasks, *tasks)

    # save results
    results = {}
    for file_path, extracted_invoice in zip(file_paths, extracted_invoices):
        if extracted_invoice is not None:
            results[file_path.name] = extracted_invoice.model_dump(mode='json')

    output_path = Path('extracted_invoices.json')
    output_path.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    agent = ExtractionAgent(model_name=os.getenv('MODEL_NAME'), api_key=os.getenv('OPENAI_API_KEY'))
    data_dir = Path('data') # change to the directory where sample invoices are stored

    asyncio.run(main(agent=agent, data_dir=data_dir))









