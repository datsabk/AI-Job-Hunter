"""Tests for document text extraction (txt/md/docx + pdf routing)."""

import pytest

from aijobhunter import documents
from aijobhunter.documents import DocumentReadError, read_document


def test_read_txt(tmp_path):
    p = tmp_path / "resume.txt"
    p.write_text("Hello resume\nPython Go", encoding="utf-8")
    assert "Hello resume" in read_document(p)


def test_read_md(tmp_path):
    p = tmp_path / "resume.md"
    p.write_text("# CV\nSenior Engineer", encoding="utf-8")
    assert "Senior Engineer" in read_document(str(p))


def test_read_docx(tmp_path):
    docx = pytest.importorskip("docx")  # python-docx
    path = tmp_path / "cv.docx"
    doc = docx.Document()
    doc.add_paragraph("Abhishek Kothari")
    doc.add_paragraph("8 years Python and Go")
    doc.save(str(path))

    text = read_document(path)
    assert "Abhishek Kothari" in text
    assert "Python and Go" in text


def test_read_docx_includes_table_text(tmp_path):
    docx = pytest.importorskip("docx")
    path = tmp_path / "cv_table.docx"
    doc = docx.Document()
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Skill"
    table.rows[0].cells[1].text = "Kubernetes"
    doc.save(str(path))
    assert "Kubernetes" in read_document(path)


def test_pdf_routes_to_pdf_reader(tmp_path, monkeypatch):
    p = tmp_path / "resume.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr(documents, "_read_pdf", lambda path: "PDF TEXT")
    assert read_document(p) == "PDF TEXT"


def test_missing_file_raises():
    with pytest.raises(DocumentReadError):
        read_document("/no/such/file.docx")
