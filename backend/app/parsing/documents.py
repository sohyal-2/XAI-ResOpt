from io import BytesIO

from docx import Document
from pypdf import PdfReader

from app.parsing.validation import CorruptDocumentError, ValidatedUpload

# Security limits against decompression / parser bombs
MAX_PDF_PAGES = 50
MAX_EXTRACTED_CHARACTERS = 250_000


def extract_document_text(upload: ValidatedUpload) -> str:
    try:
        if upload.filename.lower().endswith(".pdf"):
            text = _extract_pdf(upload.content)
        elif upload.filename.lower().endswith(".docx"):
            text = _extract_docx(upload.content)
        else:
            text = upload.content.decode("utf-8-sig").strip()
            
        if len(text) > MAX_EXTRACTED_CHARACTERS:
            text = text[:MAX_EXTRACTED_CHARACTERS]
        return text
    except (OSError, UnicodeDecodeError, ValueError, KeyError) as error:
        raise CorruptDocumentError(f"Unable to read {upload.filename}: {error}") from error


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if len(reader.pages) > MAX_PDF_PAGES:
            raise CorruptDocumentError(f"PDF exceeds maximum supported page limit of {MAX_PDF_PAGES} pages.")
        pages_text = []
        total_len = 0
        for page in reader.pages:
            extracted = page.extract_text() or ""
            pages_text.append(extracted)
            total_len += len(extracted)
            if total_len > MAX_EXTRACTED_CHARACTERS:
                break
        text = "\n".join(pages_text).strip()
    except CorruptDocumentError:
        raise
    except Exception as error:
        raise CorruptDocumentError("The PDF could not be parsed.") from error
    if not text:
        raise CorruptDocumentError("The PDF contains no extractable text.")
    return text


def _extract_docx(content: bytes) -> str:
    try:
        document = Document(BytesIO(content))
        paragraphs = []
        total_len = 0
        for paragraph in document.paragraphs:
            cleaned = paragraph.text.strip()
            if cleaned:
                paragraphs.append(cleaned)
                total_len += len(cleaned)
                if total_len > MAX_EXTRACTED_CHARACTERS:
                    break

        table_text = []
        if total_len < MAX_EXTRACTED_CHARACTERS:
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        cleaned = cell.text.strip()
                        if cleaned:
                            table_text.append(cleaned)
                            total_len += len(cleaned)
                            if total_len > MAX_EXTRACTED_CHARACTERS:
                                break
        text = "\n".join(paragraphs + table_text).strip()
    except Exception as error:
        raise CorruptDocumentError("The DOCX could not be parsed.") from error
    if not text:
        raise CorruptDocumentError("The DOCX contains no extractable text.")
    return text
