import os
from typing import List, Optional, Dict, Any, Tuple
from backend.utils.env_setup import get_logger
from backend.services.llm_service import LLMService
from hashlib import sha256
# Blob store (optional)
try:
	from backend.services.blob_store import LocalBlobStore, S3BlobStore
	exists_blob_store = True
except Exception:
	exists_blob_store = False

# LangChain vector store + embeddings
try:
	from langchain_community.vectorstores import Chroma
	exists_chroma = True
except Exception:
	exists_chroma = False
	Chroma = None  # type: ignore

try:
	from langchain_openai import OpenAIEmbeddings
	exists_openai_embeddings = True
except Exception:
	exists_openai_embeddings = False
	OpenAIEmbeddings = None  # type: ignore

# Optional libs for URL and file ingestion
try:
	import requests
	exists_requests = True
except Exception:
	exists_requests = False

try:
	from bs4 import BeautifulSoup
	exists_bs4 = True
except Exception:
	exists_bs4 = False

try:
	from pypdf import PdfReader
	exists_pypdf = True
except Exception:
	exists_pypdf = False

try:
	import docx  # python-docx
	exists_docx = True
except Exception:
	exists_docx = False

# Optional: trafilatura for higher-quality extraction
try:
	import trafilatura  # type: ignore
	exists_trafilatura = True
except Exception:
	exists_trafilatura = False

# Tokenization for token-aware chunking
try:
	import tiktoken  # type: ignore
	exists_tiktoken = True
except Exception:
	exists_tiktoken = False

# URL helpers
try:
	from urllib.parse import urlparse, urljoin
	exists_urlparse = True
except Exception:
	exists_urlparse = False
	urlparse = None  # type: ignore
	urljoin = None  # type: ignore

import xml.etree.ElementTree as ET
import re

# Namespace registry
try:
	from backend.services.namespace_registry import NamespaceRegistry
	exists_registry = True
except Exception:
	exists_registry = False
	NamespaceRegistry = None  # type: ignore

# Global registry
try:
	from backend.services.global_registry import GlobalRegistry
	exists_global_registry = True
except Exception:
	exists_global_registry = False

# Allowlist
try:
	from backend.utils.allowlist import Allowlist
	exists_allowlist = True
except Exception:
	exists_allowlist = False


class RAGService:
	"""Simple RAG service: ingest texts, URLs, files; retrieve; answer via LLMService."""
	def __init__(self, persist_dir: Optional[str] = None):
		self.logger = get_logger("RAGService")
		self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", os.path.join(os.getcwd(), "chroma_data"))
		self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
		self.provider = os.getenv("LLM_PROVIDER", "openai")
		self.llm = LLMService()
		# Chunking defaults
		self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
		self.chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
		self.split_mode = os.getenv("RAG_SPLIT_MODE", "char")  # char | token | semantic
		self.enable_dedup = os.getenv("RAG_DEDUP", "0") == "1"
		self.dedup_scope = os.getenv("RAG_DEDUP_SCOPE", "namespace")  # namespace | source | global
		self.registry = NamespaceRegistry(self.persist_dir) if exists_registry else None
		self.global_registry = GlobalRegistry(self.persist_dir) if exists_global_registry else None
		# Blob store setup
		self.blob = None
		if exists_blob_store:
			store_kind = (os.getenv("BLOB_STORE", "local") or "local").lower()
			try:
				if store_kind == "s3":
					bucket = os.getenv("BLOB_S3_BUCKET")
					prefix = os.getenv("BLOB_S3_PREFIX", "blobs")
					if bucket:
						self.blob = S3BlobStore(bucket=bucket, prefix=prefix)
				else:
					self.blob = LocalBlobStore(self.persist_dir)
			except Exception as e:
				self.logger.error(f"Blob store init failed: {e}")
				self.blob = LocalBlobStore(self.persist_dir)

		if not exists_chroma:
			self.logger.error("Chroma vector store not available. Please install 'langchain-community' and 'chromadb'.")
		if not exists_openai_embeddings:
			self.logger.error("OpenAIEmbeddings not available. Please install 'langchain-openai'.")

		self.allowlist = Allowlist(self.persist_dir) if exists_allowlist else None

	def _get_vector_store(self, namespace: str):
		if not (exists_chroma and exists_openai_embeddings):
			raise RuntimeError("Vector store or embeddings unavailable. Install prerequisites.")
		sanitized = self._sanitize_namespace(namespace)
		if sanitized != namespace:
			self.logger.info(f"Sanitized namespace '{namespace}' -> '{sanitized}' for collection name constraints")
		embeddings = OpenAIEmbeddings(model=self.embedding_model)
		collection_name = f"learnlab_{sanitized}"
		vs = Chroma(collection_name=collection_name, embedding_function=embeddings, persist_directory=self.persist_dir)
		return vs

	def _sanitize_namespace(self, namespace: str) -> str:
		"""Chroma collection names must match [a-zA-Z0-9._-] and start/end alnum. Replace invalid chars with '-'."""
		if not namespace:
			return "default"
		name = namespace.strip()
		name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name)
		name = re.sub(r"^[^a-zA-Z0-9]+", "", name)
		name = re.sub(r"[^a-zA-Z0-9]+$", "", name)
		if len(name) < 3:
			name = (name + "-ns") if name else "default"
		return name[:128]

	def _normalize_chunk_params(self, chunk_size: Optional[int], chunk_overlap: Optional[int]) -> Tuple[int, int]:
		cs = int(chunk_size) if chunk_size and chunk_size > 0 else self.chunk_size
		co = int(chunk_overlap) if chunk_overlap and chunk_overlap >= 0 else self.chunk_overlap
		if co >= cs:
			co = max(0, cs // 4)
		return cs, co

	def _split_text(self, text: str, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None, mode: Optional[str] = None) -> List[str]:
		mode = (mode or self.split_mode or "char").lower()
		cs, co = self._normalize_chunk_params(chunk_size, chunk_overlap)
		if not text:
			return []
		if mode == "token" and exists_tiktoken:
			try:
				enc = tiktoken.get_encoding("cl100k_base")
				tokens = enc.encode(text)
				if len(tokens) <= cs:
					return [text]
				chunks: List[str] = []
				start = 0
				step = max(1, cs - co)
				while start < len(tokens):
					end = min(len(tokens), start + cs)
					chunks.append(enc.decode(tokens[start:end]))
					if end == len(tokens):
						break
					start += step
				return chunks
			except Exception:
				# Fallback to char
				pass
		if mode == "semantic":
			# Improved semantic: split by double newlines and heading-like lines
			lines = text.splitlines()
			segments: List[str] = []
			buf: List[str] = []
			def emit():
				if buf:
					segments.append("\n".join(buf).strip())
					buf.clear()
			for ln in lines:
				if not ln.strip():
					emit(); continue
				if len(ln.strip()) < 120 and (ln.strip().endswith(":") or ln.strip().isupper() or ln.lstrip().startswith(('#','==','--'))):
					emit()
				buf.append(ln)
			emit()
			# pack
			acc = []
			cs, co = self._normalize_chunk_params(chunk_size, chunk_overlap)
			buf2 = ""
			for seg in segments:
				if not seg:
					continue
				if len(buf2) + 1 + len(seg) <= cs:
					buf2 = (buf2 + "\n" + seg) if buf2 else seg
				else:
					if buf2:
						acc.append(buf2)
						if co > 0 and len(buf2) > co:
							tail = buf2[-co:]
							buf2 = tail + "\n" + seg
						else:
							buf2 = seg
			if buf2:
				acc.append(buf2)
			return acc
		# Default char-based with overlap
		if len(text) <= cs:
			return [text]
		chunks: List[str] = []
		start = 0
		step = max(1, cs - co)
		while start < len(text):
			end = min(len(text), start + cs)
			chunks.append(text[start:end])
			if end == len(text):
				break
			start += step
		return chunks

	def _dedup_chunks(self, texts: List[str], metas: List[Dict[str, Any]], ids: List[str]) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
		if not self.enable_dedup:
			return texts, metas, ids
		seen: set[str] = set()
		new_t: List[str] = []
		new_m: List[Dict[str, Any]] = []
		new_i: List[str] = []
		for t, m, i in zip(texts, metas, ids):
			h = sha256(t.encode("utf-8", errors="ignore")).hexdigest()
			if h in seen:
				continue
			seen.add(h)
			m = dict(m)
			m["content_hash"] = h
			new_t.append(t)
			new_m.append(m)
			new_i.append(i)
		return new_t, new_m, new_i

	def _blob_dir(self, sanitized_ns: str) -> str:
		p = os.path.join(self.persist_dir, "blobs", sanitized_ns)
		os.makedirs(p, exist_ok=True)
		return p

	def _safe_id(self, s: str) -> str:
		return re.sub(r"[^a-zA-Z0-9._-]+", "-", s)[:128] or "doc"

	def _save_blob(self, namespace: str, base_id: str, text: str) -> str:
		try:
			if getattr(self, "blob", None) is not None:
				return self.blob.save_text(self._sanitize_namespace(namespace), self._safe_id(base_id), text or "")
			# Fallback local file save
			san = self._sanitize_namespace(namespace)
			dirp = self._blob_dir(san)
			fname = self._safe_id(base_id) + ".txt"
			path = os.path.join(dirp, fname)
			with open(path, "w", encoding="utf-8") as f:
				f.write(text or "")
			return path
		except Exception:
			return ""

	def _is_path_allowed(self, url: str) -> bool:
		pat = os.getenv("RAG_URL_PATH_ALLOWLIST", "").strip()
		if not pat:
			return True
		try:
			import re as _re
			from urllib.parse import urlparse as _uparse
			path = _uparse(url).path or "/"
			return _re.search(pat, path) is not None
		except Exception:
			return True

	def _is_domain_allowed(self, url: str) -> bool:
		# file-based allowlist first
		if self.allowlist and not self.allowlist.is_allowed(url):
			return False
		allow = os.getenv("RAG_URL_ALLOWLIST", "").strip()
		if not allow:
			return self._is_path_allowed(url)
		try:
			domains = [d.strip().lower() for d in allow.split(",") if d.strip()]
			if not domains:
				return self._is_path_allowed(url)
			if not exists_urlparse:
				return self._is_path_allowed(url)
			host = urlparse(url).netloc.lower()
			for d in domains:
				if host == d or host.endswith("." + d):
					return self._is_path_allowed(url)
		except Exception:
			return self._is_path_allowed(url)
		return False

	def ingest_texts(
		self,
		namespace: str,
		texts: List[str],
		metadatas: Optional[List[Dict[str, Any]]] = None,
		ids: Optional[List[str]] = None,
		chunk_size: Optional[int] = None,
		chunk_overlap: Optional[int] = None,
		mode: Optional[str] = None,
	) -> Dict[str, Any]:
		"""Ingest raw texts into a namespaced collection. Applies chunking."""
		self.logger.info(f"Ingesting {len(texts)} texts into namespace '{namespace}' (mode={mode or self.split_mode}, chunking)")
		vs = self._get_vector_store(namespace)
		metadatas = metadatas or [{} for _ in texts]
		# Build chunked lists
		all_texts: List[str] = []
		all_metas: List[Dict[str, Any]] = []
		all_ids: List[str] = []
		for idx, t in enumerate(texts):
			meta_base = (metadatas[idx] if idx < len(metadatas) else {}) or {}
			base_id = (ids[idx] if ids and idx < len(ids) else None) or f"doc_{idx+1}"
			# Persist original blob once per source
			blob_uri = self._save_blob(namespace, str(base_id), t or "")
			chunks = self._split_text(t or "", chunk_size, chunk_overlap, mode)
			for j, ch in enumerate(chunks):
				m = dict(meta_base)
				m.update({"chunk_index": j, "total_chunks": len(chunks), "source_id": base_id})
				if blob_uri:
					m["blob_uri"] = blob_uri
				all_texts.append(ch)
				all_metas.append(m)
				all_ids.append(f"{base_id}#chunk-{j}")

		# Optional dedup within batch
		all_texts, all_metas, all_ids = self._dedup_chunks(all_texts, all_metas, all_ids)
		# Cross-ingest dedup via registry
		cross_keep_t: List[str] = []
		cross_keep_m: List[Dict[str, Any]] = []
		cross_keep_i: List[str] = []
		new_hashes: List[str] = []
		if self.registry and self.enable_dedup:
			for t, m, i in zip(all_texts, all_metas, all_ids):
				h = m.get("content_hash") or sha256(t.encode("utf-8", errors="ignore")).hexdigest()
				ns = self._sanitize_namespace(namespace)
				src_id = m.get("source_id") or "__unknown__"
				keep = True
				if self.dedup_scope == "global":
					keep = not self.registry.has_hash_global(ns, h)
				elif self.dedup_scope == "source":
					keep = not self.registry.has_source_hash(ns, src_id, h)
				elif self.dedup_scope == "truly_global":
					keep = not (self.global_registry and self.global_registry.has_hash(h))
				else:
					keep = not self.registry.has_hash(ns, h)
				if keep:
					cross_keep_t.append(t)
					m["content_hash"] = h
					cross_keep_m.append(m)
					cross_keep_i.append(i)
					new_hashes.append((src_id, h))
			all_texts, all_metas, all_ids = cross_keep_t, cross_keep_m, cross_keep_i

		if not all_texts:
			return {"namespace": namespace, "count": 0, "ids": []}

		res = vs.add_texts(texts=all_texts, metadatas=all_metas, ids=all_ids)
		# Persist and registry update
		try:
			vs.persist()
		except Exception:
			pass
		try:
			if self.registry:
				self.registry.register(self._sanitize_namespace(namespace), added=len(all_texts))
				if new_hashes:
					h_only = [h for _, h in new_hashes]
					self.registry.add_hashes(self._sanitize_namespace(namespace), h_only)
					# per-source
					src_map: Dict[str, List[str]] = {}
					for s, h in new_hashes:
						src_map.setdefault(s, []).append(h)
					for s, lst in src_map.items():
						self.registry.add_source_hashes(self._sanitize_namespace(namespace), s, lst)
					# truly global registry
					if self.dedup_scope == "truly_global" and self.global_registry:
						self.global_registry.add_hashes(h_only)
		except Exception:
			pass
		return {"namespace": namespace, "count": len(all_texts), "ids": res}

	def ingest_urls(
		self,
		namespace: str,
		urls: List[str],
		timeout: float = 20.0,
		chunk_size: Optional[int] = None,
		chunk_overlap: Optional[int] = None,
		use_trafilatura: Optional[bool] = None,
		mode: Optional[str] = None,
	) -> Dict[str, Any]:
		if not ((exists_requests and exists_bs4) or exists_trafilatura):
			raise RuntimeError("requests+beautifulsoup4 or trafilatura are required for URL ingestion.")
		texts: List[str] = []
		metas: List[Dict[str, Any]] = []
		ids: List[str] = []
		use_traf = exists_trafilatura if use_trafilatura is None else (use_trafilatura and exists_trafilatura)
		for u in urls:
			# Enforce allowlist
			if not self._is_domain_allowed(u):
				self.logger.warning(f"URL not allowed by allowlist: {u}")
				continue
			try:
				text: Optional[str] = None
				content_type: Optional[str] = None
				etag = None
				last_modified = None
				if use_traf:
					try:
						downloaded = trafilatura.fetch_url(u)
						if downloaded:
							text = trafilatura.extract(downloaded)
					except Exception as e:
						self.logger.warning(f"Trafilatura failed for {u}: {e}")
				if (text is None or len(text.strip()) == 0) and exists_requests and exists_bs4:
					resp = requests.get(u, timeout=timeout, headers={"User-Agent": "LearnLab/1.0"})
					resp.raise_for_status()
					content_type = resp.headers.get("Content-Type")
					etag = resp.headers.get("ETag")
					last_modified = resp.headers.get("Last-Modified")
					html = resp.text
					soup = BeautifulSoup(html, "html.parser")
					for tag in soup(["script", "style", "noscript"]):
						tag.decompose()
					text = soup.get_text(separator=" ", strip=True)
					title, heads = self._extract_html_title_headings(html)
				else:
					title, heads = None, []
				if not text:
					continue
				# Incremental re-crawl check (compare hash)
				url_hash = sha256(text.encode("utf-8", errors="ignore")).hexdigest()
				if self.registry:
					ns = self._sanitize_namespace(namespace)
					meta = self.registry.get_url_meta(ns, u)
					if meta and meta.get("hash") == url_hash:
						self.logger.info(f"Skip unchanged URL {u}")
						continue
					# update URL meta
					self.registry.set_url_meta(ns, u, {"hash": url_hash, "last_modified": last_modified, "etag": etag, "t": int(os.path.getmtime(self.persist_dir)) if os.path.exists(self.persist_dir) else 0})
				m = {"source": u, "content_type": content_type or "text/html"}
				if title:
					m["title"] = title
				if heads:
					m["headings"] = heads[:20]
				texts.append(text)
				metas.append(m)
				ids.append(u)
			except Exception as e:
				self.logger.error(f"Failed to fetch URL {u}: {e}")
				continue
		if not texts:
			return {"namespace": namespace, "count": 0, "ids": []}
		return self.ingest_texts(namespace, texts, metas, ids, chunk_size=chunk_size, chunk_overlap=chunk_overlap, mode=mode)

	def _read_pdf_bytes(self, data: bytes) -> str:
		if not exists_pypdf:
			raise RuntimeError("pypdf is required to read PDFs")
		from io import BytesIO
		reader = PdfReader(BytesIO(data))
		parts: List[str] = []
		for page in reader.pages:
			try:
				parts.append(page.extract_text() or "")
			except Exception:
				continue
		return "\n".join(parts).strip()

	def _read_docx_bytes(self, data: bytes) -> str:
		if not exists_docx:
			raise RuntimeError("python-docx is required to read DOCX")
		from io import BytesIO
		doc = docx.Document(BytesIO(data))
		return "\n".join([p.text for p in doc.paragraphs]).strip()

	def _read_html_bytes(self, data: bytes) -> str:
		try:
			html = data.decode("utf-8", errors="ignore")
			if exists_trafilatura:
				text = trafilatura.extract(html)
				if text:
					return text
		except Exception:
			pass
		if not exists_bs4:
			raise RuntimeError("beautifulsoup4 is required to parse HTML")
		soup = BeautifulSoup(html, "html.parser")
		for tag in soup(["script", "style", "noscript"]):
			tag.decompose()
		return soup.get_text(separator=" ", strip=True)

	def ingest_files(self, namespace: str, files: List[Tuple[str, bytes]], chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None, mode: Optional[str] = None) -> Dict[str, Any]:
		"""Ingest uploaded files (filename, content bytes). Applies chunking."""
		texts: List[str] = []
		metas: List[Dict[str, Any]] = []
		ids: List[str] = []
		for fname, content in files:
			name_lower = (fname or "").lower()
			text = ""
			try:
				if name_lower.endswith((".txt", ".md")):
					text = content.decode("utf-8", errors="ignore")
				elif name_lower.endswith(".pdf"):
					text = self._read_pdf_bytes(content)
				elif name_lower.endswith(".docx"):
					text = self._read_docx_bytes(content)
				elif name_lower.endswith((".html", ".htm")):
					text = self._read_html_bytes(content)
				else:
					text = content.decode("utf-8", errors="ignore")
			except Exception as e:
				self.logger.error(f"Failed to parse file {fname}: {e}")
				continue
			if not text:
				continue
			texts.append(text)
			metas.append({"source": fname, "content_type": self._guess_mime(fname)})
			ids.append(fname)
		if not texts:
			return {"namespace": namespace, "count": 0, "ids": []}
		return self.ingest_texts(namespace, texts, metas, ids, chunk_size=chunk_size, chunk_overlap=chunk_overlap, mode=mode)

	def _guess_mime(self, fname: str) -> str:
		f = fname.lower()
		if f.endswith(".pdf"):
			return "application/pdf"
		if f.endswith(".docx"):
			return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
		if f.endswith((".html", ".htm")):
			return "text/html"
		if f.endswith(".md"):
			return "text/markdown"
		return "text/plain"

	def retrieve(self, namespace: str, query: str, k: int = 4):
		vs = self._get_vector_store(namespace)
		docs = vs.similarity_search(query, k=k)
		return docs

	async def answer_question(self, namespace: str, question: str, k: int = 4) -> Dict[str, Any]:
		"""Retrieve top-k, build a prompt, and ask the LLM for an answer with citations."""
		docs = self.retrieve(namespace, question, k=k)
		contexts = []
		sources = []
		for i, d in enumerate(docs):
			meta = getattr(d, "metadata", {}) or {}
			src = meta.get("source") or meta.get("id") or f"doc_{i+1}"
			sources.append({"source": src, "metadata": meta})
			contexts.append(f"[{i+1}] {d.page_content}")

		context_str = "\n\n".join(contexts) if contexts else "No context available."
		prompt = (
			"You are a helpful assistant. Using the numbered context below, answer the user's question.\n"
			"Cite sources using bracketed numbers like [1], [2] that map to the context snippets.\n\n"
			f"Context:\n{context_str}\n\n"
			f"Question: {question}\n\n"
			"Answer:"
		)

		result = await self.llm.generate(prompt, model=os.getenv("LLM_MODEL"))
		answer = ""
		if isinstance(result, dict):
			answer = result.get("choices", [{}])[0].get("text", "")
		return {"answer": answer, "sources": sources, "raw_response": result}

	# ---------------- Sitemap ingestion -----------------
	def ingest_sitemaps(
		self,
		namespace: str,
		sitemap_urls: List[str],
		max_urls: int = 200,
		same_domain_only: bool = True,
		timeout: float = 20.0,
		chunk_size: Optional[int] = None,
		chunk_overlap: Optional[int] = None,
	) -> Dict[str, Any]:
		if not exists_requests:
			raise RuntimeError("requests is required to fetch sitemaps")
		collected: List[str] = []
		seen: set[str] = set()
		for su in sitemap_urls:
			try:
				urls = self._collect_sitemap_urls(su, timeout=timeout, same_domain_only=same_domain_only, max_urls=max_urls)
				for u in urls:
					if u not in seen:
						collected.append(u)
						seen.add(u)
			except Exception as e:
				self.logger.error(f"Failed to process sitemap {su}: {e}")
				continue
		if not collected:
			return {"namespace": namespace, "count": 0, "ids": []}
		collected = collected[:max_urls]
		return self.ingest_urls(namespace, collected, timeout=timeout, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

	def _collect_sitemap_urls(self, sitemap_url: str, timeout: float, same_domain_only: bool, max_urls: int) -> List[str]:
		urls: List[str] = []
		resp_text: Optional[str] = None
		base_domain: Optional[str] = None
		try:
			if exists_urlparse:
				base_domain = urlparse(sitemap_url).netloc
			r = requests.get(sitemap_url, timeout=timeout, headers={"User-Agent": "LearnLab/1.0"})
			if r.status_code == 200 and ("xml" in r.headers.get("Content-Type", "").lower() or r.text.strip().startswith("<?xml")):
				resp_text = r.text
			else:
				if exists_urlparse and base_domain and not sitemap_url.endswith(".xml"):
					root = f"{urlparse(sitemap_url).scheme or 'https'}://{base_domain}"
					guess = urljoin(root + "/", "sitemap.xml")
					try:
						r2 = requests.get(guess, timeout=timeout, headers={"User-Agent": "LearnLab/1.0"})
						if r2.status_code == 200:
							resp_text = r2.text
					except Exception:
						pass
		except Exception:
			pass
		if not resp_text:
			return []
		try:
			root = ET.fromstring(resp_text)
			def local(tag: str) -> str:
				return tag.split('}')[-1] if '}' in tag else tag
			ln = local(root.tag).lower()
			if ln == "urlset":
				for url in root:
					if local(url.tag).lower() != "url":
						continue
					for child in url:
						if local(child.tag).lower() == "loc" and child.text:
							loc = child.text.strip()
							urls.append(loc)
			elif ln == "sitemapindex":
				sitemap_links: List[str] = []
				for sm in root:
					if local(sm.tag).lower() != "sitemap":
						continue
					for child in sm:
						if local(child.tag).lower() == "loc" and child.text:
							sitemap_links.append(child.text.strip())
				for link in sitemap_links[:max_urls]:
					try:
						r3 = requests.get(link, timeout=timeout, headers={"User-Agent": "LearnLab/1.0"})
						if r3.status_code == 200:
							sub_root = ET.fromstring(r3.text)
							for url in sub_root:
								if local(url.tag).lower() != "url":
									continue
								for child in url:
									if local(child.tag).lower() == "loc" and child.text:
										urls.append(child.text.strip())
					except Exception:
						continue
			else:
				for loc in root.iter():
					if local(loc.tag).lower() == "loc" and loc.text:
						urls.append(loc.text.strip())
		except Exception as e:
			self.logger.error(f"Failed to parse sitemap XML: {e}")
			return []
		seen: set[str] = set()
		filtered: List[str] = []
		for u in urls:
			if u in seen:
				continue
			if same_domain_only and exists_urlparse and base_domain:
				try:
					if urlparse(u).netloc != base_domain:
						continue
				except Exception:
					pass
			filtered.append(u)
			seen.add(u)
		return filtered[:max_urls]

	# ---------------- Namespace management -----------------
	def list_namespaces(self) -> List[str]:
		if self.registry:
			return self.registry.list_namespaces()
		return []

	def stats(self, namespace: str) -> Dict[str, Any]:
		try:
			vs = self._get_vector_store(namespace)
			count = -1
			# Attempt internal count
			try:
				count = vs._collection.count()  # type: ignore
			except Exception:
				pass
			reg = self.registry.stats(self._sanitize_namespace(namespace)) if self.registry else {}
			return {"namespace": namespace, "estimated_count": count, **({"registry": reg} if reg else {})}
		except Exception as e:
			return {"namespace": namespace, "error": str(e)}

	def delete_namespace(self, namespace: str) -> Dict[str, Any]:
		try:
			try:
				import chromadb  # type: ignore
				client = chromadb.PersistentClient(path=self.persist_dir)
				client.delete_collection(f"learnlab_{self._sanitize_namespace(namespace)}")
			except Exception:
				pass
			if self.registry:
				self.registry.reset(self._sanitize_namespace(namespace))
			return {"namespace": namespace, "deleted": True}
		except Exception as e:
			return {"namespace": namespace, "deleted": False, "error": str(e)}

	def _extract_html_title_headings(self, html: str) -> Tuple[Optional[str], List[str]]:
		try:
			if not exists_bs4:
				return None, []
			soup = BeautifulSoup(html, "html.parser")
			title = None
			if soup.title and soup.title.string:
				title = soup.title.string.strip()
			headings: List[str] = []
			for tag in soup.find_all(["h1","h2","h3","h4","h5","h6"]):
				text = (tag.get_text(" ") or "").strip()
				if text:
					headings.append(text)
			return title, headings
		except Exception:
			return None, []
