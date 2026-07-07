"""Generate public-domain corpus PDFs for ingestion path testing."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF


def write_pdf(path: Path, title: str, paragraphs: list[str]) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, title)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    for paragraph in paragraphs:
        pdf.multi_cell(0, 6, paragraph)
        pdf.ln(2)
    pdf.output(str(path))


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    write_pdf(
        data_dir / "nist-sp800-53-excerpt.pdf",
        "NIST SP 800-53 Excerpt — Access Control (Public Domain)",
        [
            "Source: NIST Special Publication 800-53 Rev. 5 (U.S. Government work, public domain).",
            "AC-1 Policy and Procedures: Develop, document, and disseminate access control policy.",
            "AC-2 Account Management: Manage system accounts including establishment, activation, and review.",
            "AC-3 Access Enforcement: Enforce approved authorizations for logical access.",
            "AC-6 Least Privilege: Employ the principle of least privilege for specific duties.",
            "These controls support organizational requirements for limiting access to authorized users.",
        ],
    )

    write_pdf(
        data_dir / "owasp-agentic-top10-excerpt.pdf",
        "OWASP Agentic AI Top 10 — ASI06 Excerpt",
        [
            "Source: OWASP Agentic AI Top 10 (Dec 2025). See https://owasp.org for the full document.",
            "ASI06 Memory and Context Poisoning: Attackers manipulate an agent's memory or retrieved context.",
            "Poisoned retrieved content can cause indirect prompt injection during RAG workflows.",
            "ATTEST addresses post-ingestion tamper detection for retrieved chunks and answer certificates.",
            "Mitigations include integrity monitoring, hash verification, and quarantine on mismatch.",
        ],
    )

    print(f"Created corpus PDFs in {data_dir}")


if __name__ == "__main__":
    main()
