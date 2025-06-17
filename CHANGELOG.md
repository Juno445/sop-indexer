# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup with RAG-based search functionality
- Flask web interface for querying SOPs and support articles
- Chroma vector database integration
- GPU-accelerated embedding support
- PDF, DOCX, and TXT document processing
- OCR support for image-only PDFs
- Document clustering analysis
- Metadata mapping and front-matter support

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [1.0.0] - 2024-12-XX

### Added
- Initial release of AI-Enhanced Search
- Support for Standard Operating Procedures (SOPs) and Support Articles
- RAG (Retrieval-Augmented Generation) implementation
- Ollama LLM integration
- Web-based chat interface
- Document chunking and embedding pipeline
- Semantic search capabilities

---

## How to Update This Changelog

When making changes:

1. Add new entries under `[Unreleased]`
2. Use categories: Added, Changed, Deprecated, Removed, Fixed, Security
3. When releasing, move unreleased items to a new version section
4. Follow semantic versioning (MAJOR.MINOR.PATCH)

### Example Entry Format:
```
## [1.1.0] – 2025-01-15
### Added
- New search filters
- Export functionality
### Fixed
- Memory leak in embedding generation
``` 