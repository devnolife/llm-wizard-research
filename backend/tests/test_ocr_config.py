from app.utils.document_processor import DocumentProcessor


def test_digital_pdf_does_not_trigger_ocr():
    processor = DocumentProcessor(ocr_enabled=True, ocr_min_chars_per_page=50)

    assert processor._should_use_ocr("enough extracted text " * 4, num_pages=1) is False


def test_scanned_pdf_triggers_ocr_when_enabled():
    processor = DocumentProcessor(ocr_enabled=True, ocr_min_chars_per_page=50)

    assert processor._should_use_ocr("", num_pages=1) is True


def test_scanned_pdf_does_not_trigger_ocr_when_disabled():
    processor = DocumentProcessor(ocr_enabled=False, ocr_min_chars_per_page=50)

    assert processor._should_use_ocr("", num_pages=1) is False
