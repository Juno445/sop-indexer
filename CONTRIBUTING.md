# Contributing to AI-Enhanced Search

Thank you for your interest in contributing to AI-Enhanced Search! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Ollama (for running local LLMs)
- Basic knowledge of Python, Flask, and machine learning concepts

### Setting Up Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-enhanced-search.git
   cd ai-enhanced-search
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # Windows
   # or
   source .venv/bin/activate   # Linux/macOS
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up Ollama**:
   ```bash
   ollama pull qwen3:latest
   ```

6. **Run the application**:
   ```bash
   python app.py
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-docker-support`
- `bugfix/fix-embedding-memory-leak`
- `docs/update-installation-guide`

### 2. Make Your Changes

- Follow the existing code style and patterns
- Add comments for complex logic
- Update documentation if needed
- Test your changes thoroughly

### 3. Code Quality

#### Formatting
We use `black` for code formatting:
```bash
pip install black
black .
```

#### Type Hints
Use type hints where appropriate:
```python
def process_documents(files: List[Path]) -> Dict[str, Any]:
    ...
```

#### Documentation
- Update docstrings for new functions
- Add inline comments for complex logic
- Update README.md if adding new features

### 4. Testing

While we don't have automated tests yet, please:
- Test your changes manually
- Verify the web interface works
- Test with different document types (PDF, DOCX, TXT)
- Check that embeddings are generated correctly

### 5. Commit Your Changes

Write clear, descriptive commit messages:
```bash
git add .
git commit -m "feat: add Docker support for easy deployment

- Add Dockerfile and docker-compose.yml
- Update README with Docker instructions
- Add .dockerignore file"
```

Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference any related issues
- Screenshots if UI changes are involved
- Testing instructions

## Types of Contributions

### 🐛 Bug Reports

When filing a bug report, please include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Relevant log output

### 💡 Feature Requests

For new features, please:
- Check if similar features already exist
- Explain the use case and benefits
- Consider backward compatibility
- Provide implementation ideas if possible

### 📚 Documentation

Documentation improvements are always welcome:
- Fix typos or unclear instructions
- Add examples and use cases
- Improve API documentation
- Translate documentation

### 🔧 Code Contributions

Areas where contributions are especially welcome:
- **Testing framework**: Add pytest and unit tests
- **Docker support**: Containerization for easy deployment
- **Authentication**: Add user login and access control
- **Performance**: Optimize embedding generation and search
- **UI/UX**: Improve the web interface
- **Additional document types**: Support for more file formats
- **Configuration**: Web-based settings management

## Code Style Guidelines

### Python Code Style

- Follow PEP 8
- Use descriptive variable names
- Keep functions focused and small
- Add docstrings to public functions
- Use type hints for function parameters and return values

### Example:
```python
def extract_text_from_pdf(file_path: Path) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text content as string
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        PDFProcessingError: If PDF processing fails
    """
    # Implementation here
    pass
```

### Frontend Code Style

- Use semantic HTML
- Follow CSS best practices
- Keep JavaScript minimal and readable
- Ensure accessibility (ARIA labels, keyboard navigation)

## Project Structure

```
ai-enhanced-search/
├── app.py                 # Flask web application
├── rag.py                 # RAG implementation and search logic
├── index_sop.py          # Document indexing and embedding
├── gpu_embedding_function.py  # GPU-accelerated embeddings
├── sop_clustering.py     # Document clustering analysis
├── static/               # CSS and JavaScript files
├── templates/            # HTML templates
├── chroma_sops/          # SOP vector database
├── chromadb_data/        # Support articles vector database
└── README.md
```

## Getting Help

- Check existing issues and documentation first
- Create a GitHub issue for bugs or feature requests
- For questions, start a GitHub Discussion
- Be respectful and patient when asking for help

## License

By contributing to AI-Enhanced Search, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments section (if added)

Thank you for contributing to AI-Enhanced Search! 🚀 