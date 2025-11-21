import sys
import os
import io
import json
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app
import backend.services.rag_service as rag_service_mod

client = TestClient(app)


class FakeVS:
    def __init__(self):
        self.added = []
    def add_texts(self, texts, metadatas=None, ids=None):
        ids = ids or [f"id_{i}" for i in range(len(texts))]
        for i, t in enumerate(texts):
            mid = ids[i] if i < len(ids) else f"id_{i}"
            self.added.append((mid, t))
        return ids
    def persist(self):
        return None
    def similarity_search(self, query, k=4):
        return []


@pytest.fixture(autouse=True)
def patch_vector_store(monkeypatch):
    def _fake_get_vector_store(self, namespace: str):
        return FakeVS()
    monkeypatch.setattr(rag_service_mod.RAGService, "_get_vector_store", _fake_get_vector_store)
    yield


def test_ingest_texts_chunking():
    payload = {
        "namespace": "testns",
        "texts": ["X" * 1500],
        "chunk_size": 500,
        "chunk_overlap": 50,
    }
    r = client.post("/knowledge/ingest", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["namespace"] == "testns"
    # Expect 4 chunks: 0-500, 450-950, 900-1400, 1350-1500
    assert data["count"] == 4


def test_ingest_files_txt_and_html():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
    txt_path = os.path.join(base, 'sample.txt')
    html_path = os.path.join(base, 'sample.html')

    with open(txt_path, 'rb') as f1, open(html_path, 'rb') as f2:
        files = [
            ('files', ('sample.txt', f1.read(), 'text/plain')),
            ('files', ('sample.html', f2.read(), 'text/html')),
        ]
        r = client.post("/knowledge/ingest_files", data={"namespace": "filesns", "chunk_size": 64, "chunk_overlap": 8}, files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["namespace"] == "filesns"
    assert data["count"] >= 2


def test_ingest_sitemaps_monkeypatched(monkeypatch):
    # Prepare a tiny sitemap and two pages
    sitemap_xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.test/page1</loc></url>
      <url><loc>https://example.test/page2</loc></url>
    </urlset>
    """.strip()

    page_html = """<html><body><main>Page Content</main></body></html>"""

    class FakeResponse:
        def __init__(self, text: str, status: int = 200, headers: dict | None = None):
            self.text = text
            self.status_code = status
            self.headers = headers or {"Content-Type": "text/xml"}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def fake_get(url, timeout=10, headers=None):
        if url.endswith('sitemap.xml'):
            return FakeResponse(sitemap_xml, 200, {"Content-Type": "application/xml"})
        else:
            return FakeResponse(page_html, 200, {"Content-Type": "text/html"})

    # Patch requests.get used inside rag_service
    monkeypatch.setattr(rag_service_mod, "requests", type("ReqMod", (), {"get": staticmethod(fake_get)}))

    payload = {
        "namespace": "sitemapns",
        "sitemap_urls": ["https://example.test/sitemap.xml"],
        "max_urls": 5,
        "same_domain_only": True,
    }
    r = client.post("/knowledge/ingest_sitemaps", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["namespace"] == "sitemapns"
    # Expect 2 URLs ingested; with chunking default, count >= 2
    assert data["count"] >= 2


class Doc:
    def __init__(self, text: str, meta: dict | None = None):
        self.page_content = text
        self.metadata = meta or {}


def test_ingest_urls_403(monkeypatch):
    class FakeResponse:
        def __init__(self, status=403, text="", headers=None):
            self.status_code = status
            self.text = text
            self.headers = headers or {"Content-Type": "text/html"}
        def raise_for_status(self):
            raise RuntimeError("HTTP 403")

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(403)

    import backend.services.rag_service as rag_service_mod
    monkeypatch.setattr(rag_service_mod, "requests", type("ReqMod", (), {"get": staticmethod(fake_get)}))

    payload = {
        "namespace": "blockedns",
        "urls": ["https://blocked.example/path"],
        "chunk_size": 500,
        "chunk_overlap": 50,
        "use_trafilatura": True,
    }
    r = client.post("/knowledge/ingest_urls", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["namespace"] == "blockedns"
    assert data["count"] == 0


def test_ingest_sitemaps_empty(monkeypatch):
    empty_sitemap = """
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    </urlset>
    """.strip()

    class FakeResponse:
        def __init__(self, text: str, status: int = 200, headers: dict | None = None):
            self.text = text
            self.status_code = status
            self.headers = headers or {"Content-Type": "application/xml"}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(empty_sitemap, 200, {"Content-Type": "application/xml"})

    import backend.services.rag_service as rag_service_mod
    monkeypatch.setattr(rag_service_mod, "requests", type("ReqMod", (), {"get": staticmethod(fake_get)}))

    payload = {
        "namespace": "emptyns",
        "sitemap_urls": ["https://example.test/sitemap.xml"],
        "max_urls": 5,
        "same_domain_only": True,
    }
    r = client.post("/knowledge/ingest_sitemaps", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["namespace"] == "emptyns"
    assert data["count"] == 0


def test_ingest_invalid_payload():
    # Missing required 'namespace' key
    bad_payload = {"texts": ["hello"]}
    r = client.post("/knowledge/ingest", json=bad_payload)
    assert r.status_code == 422


def test_ask_with_mocked_retriever_and_llm(monkeypatch):
    import backend.services.rag_service as rag_service_mod

    def fake_retrieve(self, namespace: str, query: str, k: int = 4):
        return [
            Doc("Content A about agents", {"source": "https://site/a"}),
            Doc("Content B about tools", {"source": "https://site/b"}),
        ]

    async def fake_generate(self, prompt: str, model: str = None, provider: str = None, **kwargs):
        return {"choices": [{"text": "Here is the answer [1]."}]}

    monkeypatch.setattr(rag_service_mod.RAGService, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag_service_mod.LLMService, "generate", fake_generate)

    payload = {"namespace": "askns", "question": "How do agents work?", "k": 2}
    r = client.post("/knowledge/ask", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data and "[1]" in data["answer"]
    assert isinstance(data.get("sources"), list) and len(data["sources"]) == 2


def test_namespace_sanitization(monkeypatch):
    # Vector store is already mocked globally by autouse fixture
    payload = {
        "namespace": "a b@!!",
        "texts": ["hello world"],
    }
    r = client.post("/knowledge/ingest", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1


def test_html_extraction_bs4_fallback(monkeypatch):
    # Force trafilatura unavailable, provide a fake BeautifulSoup
    import backend.services.rag_service as rag_service_mod

    class FakeTag:
        def decompose(self):
            return None

    class FakeSoup:
        def __init__(self, html, parser):
            self._html = html
        def __call__(self, tags):
            return []  # no tags to decompose
        def get_text(self, separator=" ", strip=True):
            return "MAIN CONTENT"

    class FakeResponse:
        def __init__(self, text: str, status: int = 200, headers: dict | None = None):
            self.text = text
            self.status_code = status
            self.headers = headers or {"Content-Type": "text/html"}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse("<html><body>Hi</body></html>")

    monkeypatch.setattr(rag_service_mod, "exists_trafilatura", False)
    monkeypatch.setattr(rag_service_mod, "exists_bs4", True)
    monkeypatch.setattr(rag_service_mod, "BeautifulSoup", FakeSoup)
    monkeypatch.setattr(rag_service_mod, "requests", type("ReqMod", (), {"get": staticmethod(fake_get)}))

    payload = {
        "namespace": "bs4ns",
        "urls": ["https://example.test/"],
        "use_trafilatura": True,
    }
    r = client.post("/knowledge/ingest_urls", json=payload)
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_html_extraction_trafilatura_none_then_bs4(monkeypatch):
    import backend.services.rag_service as rag_service_mod

    class FakeTrafilatura:
        @staticmethod
        def fetch_url(u):
            return "downloaded"
        @staticmethod
        def extract(content):
            return ""  # force fallback

    class FakeSoup:
        def __init__(self, html, parser):
            self._html = html
        def __call__(self, tags):
            return []
        def get_text(self, separator=" ", strip=True):
            return "BS4 CONTENT"

    class FakeResponse:
        def __init__(self, text: str, status: int = 200, headers: dict | None = None):
            self.text = text
            self.status_code = status
            self.headers = headers or {"Content-Type": "text/html"}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse("<html><body>Hi</body></html>")

    monkeypatch.setattr(rag_service_mod, "exists_trafilatura", True)
    monkeypatch.setattr(rag_service_mod, "trafilatura", FakeTrafilatura)
    monkeypatch.setattr(rag_service_mod, "exists_bs4", True)
    monkeypatch.setattr(rag_service_mod, "BeautifulSoup", FakeSoup)
    monkeypatch.setattr(rag_service_mod, "requests", type("ReqMod", (), {"get": staticmethod(fake_get)}))

    payload = {
        "namespace": "trafns",
        "urls": ["https://example.test/"],
        "use_trafilatura": True,
    }
    r = client.post("/knowledge/ingest_urls", json=payload)
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_ingest_files_parsers(monkeypatch):
    import backend.services.rag_service as rag_service_mod

    def fake_pdf(self, b: bytes) -> str:
        return "PDF CONTENT"
    def fake_docx(self, b: bytes) -> str:
        return "DOCX CONTENT"

    monkeypatch.setattr(rag_service_mod.RAGService, "_read_pdf_bytes", fake_pdf)
    monkeypatch.setattr(rag_service_mod.RAGService, "_read_docx_bytes", fake_docx)

    # Prepare multipart files
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
    txt_path = os.path.join(base, 'sample.txt')
    html_path = os.path.join(base, 'sample.html')

    with open(txt_path, 'rb') as f1, open(html_path, 'rb') as f2:
        files = [
            ('files', ('sample.txt', f1.read(), 'text/plain')),
            ('files', ('sample.html', f2.read(), 'text/html')),
            ('files', ('sample.pdf', b'%PDF fake', 'application/pdf')),
            ('files', ('sample.docx', b'PK\x03\x04 fake', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')),
            ('files', ('unknown.bin', b'BIN CONTENT', 'application/octet-stream')),
            ('files', ('empty.txt', b'', 'text/plain')),
        ]
        r = client.post(
            "/knowledge/ingest_files",
            data={"namespace": "files-parse-ns", "chunk_size": 10000, "chunk_overlap": 0},
            files=files,
        )
    assert r.status_code == 200
    data = r.json()
    # Expect all non-empty parses included: txt, html, pdf, docx, bin => 5
    assert data["count"] == 5


def test_sitemapindex_nested(monkeypatch):
    import backend.services.rag_service as rag_service_mod

    sitemapindex_xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.test/sub1.xml</loc></sitemap>
    </sitemapindex>
    """.strip()

    sub_sitemap = """
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.test/pageA</loc></url>
      <url><loc>https://example.test/pageB</loc></url>
    </urlset>
    """.strip()

    class FakeSoup:
        def __init__(self, html, parser):
            self._html = html
        def __call__(self, tags):
            return []
        def get_text(self, separator=" ", strip=True):
            return "PAGE CONTENT"

    class FakeResponse:
        def __init__(self, text: str, status: int = 200, headers: dict | None = None):
            self.text = text
            self.status_code = status
            self.headers = headers or {"Content-Type": "application/xml"}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def fake_get(url, timeout=10, headers=None):
        if url.endswith('sitemap.xml'):
            return FakeResponse(sitemapindex_xml, 200, {"Content-Type": "application/xml"})
        if url.endswith('sub1.xml'):
            return FakeResponse(sub_sitemap, 200, {"Content-Type": "application/xml"})
        return FakeResponse("<html><body>Hi</body></html>", 200, {"Content-Type": "text/html"})

    monkeypatch.setattr(rag_service_mod, "requests", type("ReqMod", (), {"get": staticmethod(fake_get)}))
    monkeypatch.setattr(rag_service_mod, "exists_bs4", True)
    # Fake BeautifulSoup for page content
    monkeypatch.setattr(rag_service_mod, "BeautifulSoup", FakeSoup)

    payload = {
        "namespace": "sitemap-nested-ns",
        "sitemap_urls": ["https://example.test/sitemap.xml"],
        "max_urls": 10,
        "same_domain_only": True,
    }
    r = client.post("/knowledge/ingest_sitemaps", json=payload)
    assert r.status_code == 200
    data = r.json()
    # Two pages expected, chunk size default -> at least 2 chunks
    assert data["count"] >= 2
