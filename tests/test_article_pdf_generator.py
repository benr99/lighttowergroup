import sys
import tempfile
import unittest
from pathlib import Path

try:
    from pypdf import PdfReader
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from article_pdf_generator import build_article_pdf
except ImportError:
    build_article_pdf = None


class ArticlePdfGeneratorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not _HAS_PYPDF:
            raise unittest.SkipTest("pypdf not installed — skipping PDF generator tests")
    def test_pdf_keeps_article_text_in_reading_order(self):
        article = {
            "slug": "test-insight",
            "title": "The loan buys time, not a solution",
            "subtitle": "What a lease-up refinance reveals about the market.",
            "category": "Capital Markets",
            "date": "July 12, 2026",
        }
        body = """
        <article><div class='article-body'>
          <p>The first paragraph is the approved opening of the Insight.</p>
          <p>The second paragraph carries the analysis forward in the original voice.</p>
          <p>The third paragraph explains what the reader should watch next.</p>
        </div></article>
        """
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "test-insight_article.pdf"
            build_article_pdf(body, article, pdf_path)
            reader = PdfReader(str(pdf_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            self.assertGreaterEqual(len(reader.pages), 2)
            self.assertIn("first paragraph is the approved opening", text)
            self.assertIn("third paragraph explains", text)


if __name__ == "__main__":
    unittest.main()
