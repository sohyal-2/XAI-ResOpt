import os
import re
from dataclasses import dataclass

SUPPORTED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_TEXT_BYTES = 10 * 1024 * 1024

# Executable / binary magic signatures that must never be in plain text uploads
DISALLOWED_BINARY_SIGNATURES = [
    b"MZ",          # DOS / Windows PE executable
    b"\x7fELF",     # Linux ELF executable
    b"\xca\xfe\xba\xbe", # Java class / Mach-O fat binary
    b"\xfe\xed\xfa\xce", # Mach-O 32-bit
    b"\xfe\xed\xfa\xcf", # Mach-O 64-bit
    b"\x50\x4b\x03\x04", # Zip disguised as text
    b"\x50\x4b\x05\x06", # Zip disguised as text
    b"\x1f\x8b",     # Gzip disguised as text
]


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content_type: str
    content: bytes


class IngestionError(ValueError):
    """A user-correctable ingestion failure."""


class UnsupportedFileError(IngestionError):
    pass


class CorruptDocumentError(IngestionError):
    pass


def sanitize_filename(raw_name: str) -> str:
    """Sanitizes filename against path traversal, control characters, and dangerous characters."""
    if not raw_name:
        return "unnamed_document.txt"
    # Remove null bytes and path components
    cleaned = raw_name.replace("\x00", "")
    # Normalize slashes and take only the basename
    cleaned = cleaned.replace("\\", "/")
    base = os.path.basename(cleaned)
    # Strip any remaining dangerous characters, keeping only alphanumeric, hyphen, underscore, and dot
    base = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    # Strip leading dots to prevent hidden files
    base = base.lstrip(".")
    if not base:
        base = "document"
    return base


def validate_upload(filename: str, content_type: str | None, content: bytes, max_bytes: int) -> ValidatedUpload:
    if not filename or not content:
        raise IngestionError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise IngestionError(f"The uploaded file exceeds the {max_bytes // (1024 * 1024)} MB limit.")

    clean_filename = sanitize_filename(filename)

    extension = clean_filename.lower().rsplit(".", 1)
    extension = f".{extension[-1]}" if len(extension) == 2 else ""
    normalized_type = (content_type or "").split(";", 1)[0].lower()

    if extension not in SUPPORTED_RESUME_EXTENSIONS:
        raise UnsupportedFileError("Supported resume formats are PDF, DOCX, and plain text.")
    if normalized_type and normalized_type not in SUPPORTED_RESUME_MIME_TYPES:
        raise UnsupportedFileError("The uploaded MIME type is not supported.")

    # Deep magic-byte validation
    if extension == ".pdf":
        if not content.startswith(b"%PDF-") or len(content) < 10:
            raise CorruptDocumentError("The file does not contain a valid PDF signature.")
    elif extension == ".docx":
        if not content.startswith(b"PK\x03\x04") or len(content) < 30:
            raise CorruptDocumentError("The file does not contain a valid DOCX container.")
    elif extension == ".txt":
        # Check for binary null bytes
        if b"\x00" in content:
            raise CorruptDocumentError("Plain text files must not contain binary null bytes.")
        # Check for disguised executables
        for sig in DISALLOWED_BINARY_SIGNATURES:
            if content.startswith(sig):
                raise CorruptDocumentError("Plain text files must not contain executable binary content.")
        # Validate UTF-8 encoding
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as err:
            raise CorruptDocumentError(f"Plain text file is not valid UTF-8: {err}") from err

    return ValidatedUpload(clean_filename, normalized_type or _mime_for_extension(extension), content)


def _mime_for_extension(extension: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
    }[extension]
