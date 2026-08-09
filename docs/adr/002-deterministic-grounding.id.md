# ADR 002: Validasi Sitasi Deterministik & Safeguard Abstention Eksplisit

**Bahasa:** 🇮🇩 Bahasa Indonesia · [🇬🇧 English](002-deterministic-grounding.md)

## Status
**Diterima**

## Konteks
Question answering regulasi keuangan membutuhkan provenance hukum yang kuat dan tidak boleh menghasilkan jawaban tanpa grounding. Aplikasi LLM standar rentan terhadap hallucination, perubahan format sitasi, dan jawaban tanpa grounding ketika evidence hasil retrieval berada di luar domain atau di bawah threshold relevansi.

Mengandalkan evaluasi mandiri LLM ("LLM-as-a-judge") menambah latency yang tidak deterministik, biaya API, dan kerentanan terhadap bias model atau prompt injection.

## Keputusan
Kami menerapkan **Deterministic Grounded RAG Pipeline** dengan verifikasi multi-layer:
1. **Early Score-Threshold Abstention**: jika context block hasil reranking teratas berada di bawah minimum relevance threshold (`rag_min_rerank_threshold = 0.30`), sistem langsung abstain tanpa memanggil LLM.
2. **Strict Regex Citation Syntax Enforcement**: prompt LLM mewajibkan tag sitasi inline dengan format `[C1]`, `[C2]` yang sesuai dengan context block. Jawaban diparse menggunakan regular expression deterministik (`CITATION_REGEX = re.compile(r"\[C(\d+)\]")`).
3. **Citation Provenance Binding**: setiap tag sitasi yang diekstrak divalidasi terhadap metadata `ContextBlock` hasil retrieval agar context ID yang dirujuk benar-benar ada dalam payload prompt.
4. **Context Leak & Injection Defense**: teks hukum hasil retrieval dibungkus sebagai untrusted data, sementara system prompt secara eksplisit menginstruksikan model untuk mengabaikan instruksi yang terdapat di dalam teks regulasi.

## Konsekuensi
### Positif
- **Reliability deterministik**: validitas grounding dan keberadaan sitasi diverifikasi secara matematis melalui regex dan provenance lookup, tanpa latency dan biaya LLM-as-a-judge.
- **Safeguard keamanan**: sistem dapat abstain secara konsisten pada kueri out-of-domain (misalnya regulasi penerbangan luar angkasa komersial) dengan akurasi 100%.
- **Auditability**: sitasi yang dihasilkan dapat ditelusuri langsung ke regulation ID, nomor pasal, structural path, dan rentang halaman sumber.

### Negatif / Trade-off
- Jika LLM menghasilkan jawaban yang valid tetapi menghilangkan tag sitasi, citation validator akan menahan jawaban dan memicu abstention demi menjaga keamanan.
