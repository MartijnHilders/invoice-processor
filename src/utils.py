import io
from PIL import Image
from pdf2image import convert_from_bytes

def load_document(file_bytes: bytes, extension: str) -> Image.Image:
    """
    Loads a document (PDF or image) and converts it to a PIL Image object.
    For simplicity, we assume that everything is a single page, which is also what our input data depicts. In a more
    complex scenario, we would need to build in logic to handle multi-page documents, and decide what to process.

    decided to put the DPI
    :param file_bytes: The raw bytes of the file to be loaded.
    :param extension: The file extension (e.g., '.pdf', '.jpg', '.jpeg', '.tiff') to determine how to process the file.
    :return:
    """

    # Load PDF and convert to image
    if extension == '.pdf':

        # todo find the best setting for this
        images = convert_from_bytes(file_bytes, dpi=300)  # Adjust dpi as needed for quality vs performance and lower inference costs
        return images[0] # we only want the first page.

    # if not, we can load the image directly using PIL since we strictly have tiff/jpeg/jpg formats
    image = Image.open(io.BytesIO(file_bytes))

    # Standard RGB conversion to ensure consistent color mode.
    if image.mode != 'RGB':
        image = image.convert('RGB')

    return image




