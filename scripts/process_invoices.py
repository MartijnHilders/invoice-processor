import os
import dotenv
import logging
import asyncio
import json
from pathlib import Path
from src.extraction_agent import ExtractionAgent
from src.utils import load_document, gather_with_concurrency

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


async def main(agent: ExtractionAgent, data_dir: Path, concurrent_tasks: int = 5):
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
    data_dir = Path('data')

    asyncio.run(main(agent=agent, data_dir=data_dir))









