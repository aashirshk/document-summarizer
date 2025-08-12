<<<<<<< HEAD
# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      ...tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      ...tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      ...tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
=======
# Context-Aware Multi-Document RAG System

A powerful document analysis system that uses AI to summarize documents and answer questions about their content.

## Features

- Upload multiple documents (PDF, TXT, DOCX)
- AI-powered document summarization
- Intelligent question answering based on document content
- Context-aware responses with source citations
- Clean web interface built with Streamlit

## Local Setup Instructions

### 1. Install Python Dependencies

Open terminal in Visual Studio Code and run:

```bash
pip install streamlit openai pypdf2 python-docx scikit-learn numpy
```

Or if you prefer using pip with requirements:

```bash
pip install -r requirements.txt
```

### 2. Set Up OpenAI API Key

You need to set your OpenAI API key as an environment variable.

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=your_api_key_here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your_api_key_here"
```

**Mac/Linux:**
```bash
export OPENAI_API_KEY=your_api_key_here
```

**Alternative: Create a .env file**
Create a file named `.env` in your project folder:
```
OPENAI_API_KEY=your_api_key_here
```

### 3. Run the Application

In your terminal, navigate to the project folder and run:

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Usage

1. **Upload Documents**: Use the sidebar to upload PDF, TXT, or DOCX files
2. **Generate Summaries**: Click "Generate Summaries for All Documents" 
3. **Ask Questions**: Use the "Ask Questions" tab to query your documents
4. **Get AI Answers**: The system will find relevant content and provide detailed answers

## Project Structure

- `app.py` - Main Streamlit application
- `document_processor.py` - Document text extraction and chunking
- `vector_store.py` - Embedding creation and similarity search
- `rag_system.py` - AI-powered summarization and Q&A
- `.streamlit/config.toml` - Streamlit configuration

## Requirements

- Python 3.7+
- OpenAI API key with available quota
- Internet connection for API calls

## Troubleshooting

**API Quota Error**: If you see quota exceeded errors, check your OpenAI billing at https://platform.openai.com/account/billing

**Missing Dependencies**: Run `pip install -r requirements.txt` to install all required packages

**Port Already in Use**: If port 8501 is busy, Streamlit will automatically use the next available port
>>>>>>> 4c365fb (Add detailed instructions for running the document analysis system locally)
