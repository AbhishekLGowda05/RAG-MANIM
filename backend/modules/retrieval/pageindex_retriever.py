import json
import logging
from pathlib import Path

from PageIndex.pageindex.client import PageIndexClient

PDF_PATH = (
    Path(__file__).resolve().parents[3]
    / "PageIndex"
    / "examples"
    / "documents"
    / "SCERT Kerala State Syllabus 10th Standard Physics Textbooks English Medium Part 1.pdf"
)

WORKSPACE = (
    Path(__file__).resolve().parents[3]
    / "pageindex_workspace"
)

client = PageIndexClient(
    workspace=str(WORKSPACE)
)

DOC_ID = None

logger = logging.getLogger(__name__)


def initialize_pageindex():
    global DOC_ID

    if DOC_ID:
        return DOC_ID

    DOC_ID = client.index(str(PDF_PATH))

    return DOC_ID


def retrieve_curriculum_context(topic: str):

    doc_id = initialize_pageindex()

    logger.info(
        "Searching curriculum context for topic=%s",
        topic,
    )

    structure = json.loads(
        client.get_document_structure(doc_id)
    )

    matches = []

    def walk(nodes):
        for node in nodes:

            title = (
                node.get("title", "")
                .lower()
            )

            topic_words = set(topic.lower().split())

            if any(word in title for word in topic_words):
                matches.append(node)

            walk(node.get("nodes", []))

    walk(structure)

    logger.info(
        "Found %d matching nodes",
        len(matches),
    )

    if not matches:
        return ""

    node = matches[0]

    start_page = node.get("start_index")
    end_page = node.get("end_index")

    if not start_page:
        return ""

    content = client.get_page_content(
        doc_id,
        f"{start_page}-{end_page}"
    )

    return content