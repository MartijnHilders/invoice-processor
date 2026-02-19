import datetime
import json
from typing import Optional

import pandas as pd
import streamlit as st
import asyncio
import yaml
import os
import logging
from dotenv import load_dotenv
from pydantic_ai import AgentRunResult

from src.extraction_agent import ExtractionAgent
from src.models import InvoiceResult, InvoiceResultMetadata, InvoiceData
from src.logic import logic_rules
from streamlit.runtime.uploaded_file_manager import UploadedFile
from src.utils import load_document, gather_with_concurrency, create_hash

load_dotenv()
logger = logging.getLogger('Invoice Processor - Streamlit App')
st.set_page_config(page_title="Invoice Processor", layout="wide")

# resources that only need to be initialised once.
@st.cache_resource
def initialise_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)

    # set up logfire when the token is provided, this for ease of observability when running the app
    if os.getenv('LOGFIRE_TOKEN'):
        import logfire
        logfire.configure()
        logfire.instrument_pydantic_ai()
        logger.info('Logfire configured and Pydantic AI instrumented')


@st.cache_resource
def get_agent():
    # Initialise the agent

    agent = ExtractionAgent(
        model_name=os.getenv('MODEL_NAME'),
        api_key=os.getenv('OPENAI_API_KEY') or os.getenv("MODEL_API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL")
    )

    logger.info('Extraction Agent initialized')
    return agent

@st.cache_data
def get_config():
    # Initialise the config for the thresholds # todo maybe make this a bit more robust
    with open("config/approval_thresholds.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config



# create the hash set if it doesn't exist yet
if 'processed_hashes' not in st.session_state:
    st.session_state.processed_hashes = set()

if 'history' not in st.session_state:
    st.session_state.history = []

if 'current_batch' not in st.session_state:
    st.session_state.current_batch = []


# Interface and initialization
initialise_logging()
config = get_config()

st.title("Invoice Processor")
uploaded_files = st.file_uploader(
    "Upload Invoices",
    type=["pdf", "jpg", "png", "tiff", "tif"], # restrict to data types we have seen in the sample invoices
    accept_multiple_files=True,
    max_upload_size=20 # 20 mb per file as we only process one pagers
)

# create a button to clear the history of processed items
if st.sidebar.button("Clear Session History"):
    st.session_state.processed_hashes = set()
    st.session_state.history = []
    st.session_state.current_batch = []

    st.sidebar.success("History cleared!")
    logger.info('Processing history cleared by user.')
    st.rerun()


async def extract_invoice(agent: ExtractionAgent, file: UploadedFile) -> Optional[AgentRunResult[InvoiceData]]:
    """
    Takes a single invoice and processes it through the agent to extract the relevant data.

    :return: The extracted data as an InvoiceData object, or None if there was an error during processing.
    """
    logger.info(f"Processing file: {file.name}")
    try:
        # Prepare each image
        file.seek(0) # ensure we are at the start of the file even if something weird happens
        file_bytes = file.read()
        file_extension = os.path.splitext(file.name)[-1].lower()
        img = load_document(file_bytes=file_bytes, extension=file_extension, max_dimension=1750)

        # Extract data using the agent
        return await agent.extract_data(img)

    except Exception as e:
        logger.error(f"Error processing file {file.name}: {e}")
        return None

async def extract_invoice_batch(agent: ExtractionAgent, files: list[UploadedFile], concurrency_limit: int = 5) -> list:
    """
    Process a batch of invoices concurrently while limiting the number of simultaneous tasks to avoid hitting rate limits.

    :param concurrency_limit: The maximum number of concurrent tasks to run at the same time.
    :param agent: The extraction agent to use for processing the invoices.
    :param files: A list of uploaded files to process.
    :return: list of results corresponding to each file, where each result is either the extracted InvoiceData or None if there was an error.
    """
    tasks =[extract_invoice(agent, file) for file in files]
    # process the tasks concurrently, limit it to 5 at a time to avoid hitting rate limits.
    return await gather_with_concurrency(concurrency_limit, *tasks)


if uploaded_files:
    if st.button(f"Process {len(uploaded_files)} Invoices"):
        agent = get_agent() # retrieve the agent
        st.session_state.current_batch = [] # rest the current batch which stores the results

        with st.spinner(f"Processing {len(uploaded_files)} files... This may take a moment."):

            # Execute the batch async
            results = asyncio.run(extract_invoice_batch(agent=agent, files=uploaded_files))

            # loop over the results and files to display them in the interface
            for uploaded_file, run_result in zip(uploaded_files, results):

                # catch if run_result = None due to a processing Error
                if run_result is None:
                    # list error rejection
                    invoice_result = InvoiceResult(
                        status='REJECT',
                        reasons=["Error processing the invoice. Please ensure the file is a valid invoice and try again."],
                        extracted_data=InvoiceData().model_dump(),
                        metadata=InvoiceResultMetadata(
                            filename=uploaded_file.name,
                            hash_value=f"ERROR_{uploaded_file.name}_{int(datetime.datetime.now().timestamp())}",
                            model_used=agent.model_display_name
                        )
                    )

                else:
                    invoice_data = run_result.output  # extract the data
                    reasons = logic_rules(invoice=invoice_data, config=config) # apply the logic rules
                    hash_val = create_hash(invoice=invoice_data) # create hash for deduplication

                    # Check if the hash value is already seen, and is not only ___ which may happen with total garbage input
                    if hash_val.strip('_'):
                        if hash_val not in st.session_state.processed_hashes:
                            # add the hash to the set of processed hashes to prevent future duplicates in the same session
                            st.session_state.processed_hashes.add(hash_val)
                        else:
                            reasons.extend(["Duplicate invoice detected based on hash. This invoice has already been processed."])

                    if reasons:
                        logger.info(f"Invoice {uploaded_file.name} REJECTED for reasons: {reasons}")
                    else:
                        logger.info(f"Invoice {uploaded_file.name} ACCEPTED with no issues.")


                    invoice_result = InvoiceResult(
                        status='REJECT' if reasons else 'ACCEPT',
                        reasons=reasons,
                        extracted_data=invoice_data.model_dump(),
                        metadata=InvoiceResultMetadata(
                            filename=uploaded_file.name,
                            hash_value=hash_val,
                            model_used=agent.model_display_name
                        )
                    )

                # add the invoice result to the history of processed invoices
                st.session_state.history.append(invoice_result)
                st.session_state.current_batch.append(invoice_result)

if st.session_state.current_batch:
    st.subheader('Current Batch Results')

    # display the results in an expander for each file.
    for i, res in enumerate(st.session_state.current_batch):
        status = res.status

        with st.expander(f"{res.metadata.filename}: Status: {':red[REJECTED]' if status == 'REJECT' else ':green[ACCEPTED]'}"):
            if status == 'ACCEPT':
                st.success("Accepted")
            else:
                st.error("Rejected for the following reasons:")
                for r in res.reasons: st.write(f"- {r}")

            # add a download button for every invoice
            st.download_button(
                label=f"Download JSON",
                data=res.model_dump_json(indent=2),
                file_name=f"result_{res.metadata.filename}_{int(res.metadata.created_time.timestamp())}.json",
                key=f"download_{res.metadata.hash_value}_{i}",  # Unique key is required for buttons in loops
                mime='application/json'
            )

            st.subheader("Extracted Invoice Data")
            st.json(res.model_dump(mode='json')) # display the json data

@st.fragment # ensures that this is only rendered when there is action in the history session state (will not render every time)
def session_history_log():
    if st.session_state.history:
        st.divider()
        st.subheader("Session History Log")

        # Create a summary dictionary from the history session state
        history_data = [
            {
                "Status": "✓" if h.status == "ACCEPT" else "✗",
                "Filename": h.metadata.filename,
                "Total Amount Gross": f"{h.extracted_data.total_amount_gross:.2f}" if h.extracted_data.total_amount_gross is not None else "-",
                "Hash value": h.metadata.hash_value,
                "Processed At": h.metadata.created_time.strftime("%H:%M:%S"),
                "model": h.metadata.model_used
            }
            for h in st.session_state.history
        ]

        # Display as a clean table
        st.dataframe(pd.DataFrame(history_data), width='stretch', hide_index=True)

        # dump the history into json to make it downloadable as a file.
        full_json = json.dumps([h.model_dump() for h in st.session_state.history], indent=2, default=str)

        st.download_button(
            label="Download History (JSON)",
            data=full_json,
            file_name=f"invoice_results_history_{int(datetime.datetime.now().timestamp())}.json",
            mime="application/json"
        )

session_history_log()