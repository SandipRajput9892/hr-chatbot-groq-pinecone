#!/usr/bin/env python3
"""Standalone CLI to ingest HR documents (PDFs or text files) into Pinecone."""
import argparse
import os
import sys

# Allow running from project root: python scripts/ingest.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.pinecone_client import init_pinecone_index
from app.services.ingest_service import ingest_pdf, ingest_text
from app.utils.logger import get_logger

logger = get_logger("ingest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest HR documents into Pinecone")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pdf", metavar="FILE", help="Path to a single PDF file")
    group.add_argument("--text", metavar="FILE", help="Path to a plain text file")
    group.add_argument("--dir", metavar="DIR", help="Directory of PDF files to ingest")
    parser.add_argument("--source", metavar="NAME", help="Override source name stored in metadata")
    args = parser.parse_args()

    logger.info("Initialising Pinecone …")
    init_pinecone_index()

    if args.dir:
        pdf_files = [f for f in os.listdir(args.dir) if f.lower().endswith(".pdf")]
        if not pdf_files:
            logger.error("No PDF files found in directory")
            sys.exit(1)
        for fname in sorted(pdf_files):
            path = os.path.join(args.dir, fname)
            source = args.source or fname
            logger.info(f"Ingesting {fname} …")
            result = ingest_pdf(path, source)
            logger.info(f"Result: {result}")
        return

    if args.pdf:
        source = args.source or os.path.basename(args.pdf)
        logger.info(f"Ingesting {args.pdf} …")
        result = ingest_pdf(args.pdf, source)
        logger.info(f"Result: {result}")
        return

    if args.text:
        with open(args.text, "r", encoding="utf-8") as fh:
            text = fh.read()
        source = args.source or os.path.basename(args.text)
        logger.info(f"Ingesting {args.text} …")
        result = ingest_text(text, source)
        logger.info(f"Result: {result}")


if __name__ == "__main__":
    main()
