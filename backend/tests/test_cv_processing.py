import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from pypdf import PdfWriter
from pypdf.generic import NameObject, DictionaryObject, ArrayObject, FloatObject, NumberObject

from app.main import app
from app.modules.cv_processing.parser import extract_text_from_pdf, PDFParsingError
from app.modules.cv_processing.extractor import verify_citation
from app.modules.cv_processing.schemas import (
    CvExtractionSchema,
    SkillExtraction,
    WorkExperienceExtraction,
    EducationExtraction,
    ContactInfo,
)


def create_mock_pdf_bytes(text: str) -> bytes:
    """Helper to generate a valid digital PDF with embedded text for testing."""
    stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET"
    stream_len = len(stream_content)
    pdf_str = (
        "%PDF-1.4\n"
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n{stream_content}\nendstream\nendobj\n"
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        "xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        "0000000115 00000 n \n0000000244 00000 n \n0000000350 00000 n \n"
        "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n440\n%%EOF"
    )
    return pdf_str.encode("latin-1")


def test_verify_citation_exact_and_fuzzy():
    raw_cv = (
        "Senior Android Engineer with 5 years experience building apps in Kotlin and Coroutines. "
        "Architected modern UI with Jetpack Compose at TechCorp. Familiar with Room database."
    )

    # Exact quote
    assert verify_citation("building apps in Kotlin and Coroutines", raw_cv) is True

    # Case insensitive and minor punctuation
    assert verify_citation("Building Apps In Kotlin, and Coroutines!", raw_cv) is True

    # Partial 4-word window match
    assert verify_citation("experience building apps in Kotlin and other things", raw_cv) is True

    # Complete hallucination / fabricated skill
    assert verify_citation("7 years of Kubernetes cluster administration", raw_cv) is False
    assert verify_citation("Extensive experience in Rust and Go programming", raw_cv) is False


def test_pdf_parser_rejects_empty():
    with pytest.raises(PDFParsingError, match="Uploaded file is empty"):
        extract_text_from_pdf(b"")


def test_pdf_parser_valid_text():
    sample_text = "Experienced Android developer skilled in Kotlin, Compose, and clean architecture."
    pdf_bytes = create_mock_pdf_bytes(sample_text)
    text, pages = extract_text_from_pdf(pdf_bytes)
    assert pages == 1
    assert "Experienced Android developer" in text


@pytest.mark.asyncio
async def test_upload_cv_rejects_non_pdf():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/cv/upload",
            files={"file": ("resume.docx", b"dummy word content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"user_email": "candidate@example.com"},
        )
        assert response.status_code == 400
        assert "Only PDF documents (.pdf) are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_cv_success_with_mocked_llm():
    sample_text = "Olena Kovalenko. Senior Android Engineer. 4 years experience with Kotlin and Jetpack Compose at KyivStar."
    pdf_bytes = create_mock_pdf_bytes(sample_text)

    # Mock Gemini response to verify the end-to-end pipeline and hallucination filter
    mock_extracted = CvExtractionSchema(
        full_name="Olena Kovalenko",
        target_role="Senior Android Engineer",
        total_years_of_experience=4.0,
        contact=ContactInfo(email="olena@example.com", location="Kyiv, Ukraine"),
        skills=[
            SkillExtraction(
                name="Kotlin",
                category="Languages",
                years_of_experience=4.0,
                source_quote="4 years experience with Kotlin",
            ),
            # This skill is an intentional hallucination not present in sample_text
            SkillExtraction(
                name="Rust",
                category="Languages",
                years_of_experience=2.0,
                source_quote="2 years developing production systems in Rust",
            ),
        ],
        work_experiences=[
            WorkExperienceExtraction(
                company="KyivStar",
                role="Senior Android Engineer",
                start_date="2020",
                end_date="Present",
                responsibilities=["Built Android apps"],
                skills_used=["Kotlin", "Jetpack Compose"],
                source_quote="Senior Android Engineer. 4 years experience with Kotlin and Jetpack Compose at KyivStar.",
            )
        ],
        education=[
            EducationExtraction(
                institution="Taras Shevchenko National University",
                degree="B.Sc.",
                field_of_study="Computer Science",
            )
        ],
    )

    with patch(
        "app.modules.cv_processing.service.extract_structured_cv",
        new_callable=AsyncMock,
        return_value=(mock_extracted, 1, 1),  # 1 verified skill (Kotlin), 1 discarded (Rust)
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/cv/upload",
                files={"file": ("olena_cv.pdf", pdf_bytes, "application/pdf")},
                data={"user_email": "olena@example.com"},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["target_role"] == "Senior Android Engineer"
            assert data["years_of_experience"] == 4.0
            assert data["verified_skills_count"] == 1
            assert data["discarded_hallucinations_count"] == 1

            # Verify GET /api/v1/cv/profile returns the saved profile
            profile_res = await client.get("/api/v1/cv/profile?email=olena@example.com")
            assert profile_res.status_code == 200
            profile_data = profile_res.json()
            assert profile_data["target_role"] == "Senior Android Engineer"
