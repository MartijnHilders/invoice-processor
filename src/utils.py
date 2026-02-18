import asyncio
import io
import types
import pymupdf
from PIL import Image
from src.models import InvoiceData


def load_document(file_bytes: bytes, extension: str, max_dimension: int = 1750) -> Image.Image:
    """
    Loads a document (PDF or image) and converts it to a PIL Image object.
    For simplicity, we assume that everything is a single page, which is also what our input data depicts. In a more
    complex scenario, we would need to build in logic to handle multi-page documents, and decide what to process.

    To make sure the documents are not too large for the model and to reduce inference costs, we resize the image
    if it exceeds the specified max dimension while maintaining aspect ratio. While also scaling PDFs to the fixed
    max dimension since using DPI can lead to extremely large images, which can cause issues for the model and increase inference costs.

    :param file_bytes: The raw bytes of the file to be loaded.
    :param extension: The file extension (e.g., '.pdf', '.jpg', '.jpeg', '.tiff') to determine how to process the file.
    :param max_dimension: The maximum dimension (width or height) for the output image. If the original image
    exceeds this dimension, it will be resized while maintaining aspect ratio.
    :return:
    """

    # Load PDF and convert to image
    if extension == '.pdf':
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        width, height = page.rect.width, page.rect.height

        # Using the dpi setting is too dangerous since it can lead to extremely large images. Therefore, opted to
        # use the matrix to scale correctly to max dimensions.
        scale = max_dimension / max(width, height)
        pdf_matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=pdf_matrix)

        image =  Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    else:
        # if not, we can load the image directly using PIL since we strictly have tiff/jpeg/jpg formats
        image = Image.open(io.BytesIO(file_bytes))

    # resize to ensure that we are not sending extremely large images to the model, which hurts inference costs.
    # BICUBIC since this is good for downscaling and maintaining quality.
    if max(image.width, image.height) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), resample=Image.Resampling.BICUBIC)

    # Standard RGB conversion to ensure consistent color mode.
    if image.mode != 'RGB':
        image = image.convert('RGB')

    return image

async def gather_with_concurrency(n: int, *coros: tuple[types.CoroutineType, ...]):
    """
    The function wraps around asyncio.gather() that limits the number of coroutines
    that can be running at any given time to n. Useful for limiting the number of concurrent connections to an
    external service (API endpoint).

    :param n: The number of concurrent tasks
    :param *coros: The coroutines to be executed with limited concurrency. This can be any number of coroutines passed as separate arguments.
    :return: The results of the gathered coroutines
    """

    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(*(sem_coro(c) for c in coros))


def create_hash(invoice: InvoiceData):
    """
    Create a hash value based on the vendor name, invoice number
    :param invoice:
    :return:
    """

    pass

