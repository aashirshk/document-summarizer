import streamlit as st
import os
from document_processor import DocumentProcessor
from vector_store import VectorStore
from rag_system import RAGSystem
import tempfile

# Initialize session state
if 'documents' not in st.session_state:
    st.session_state.documents = {}
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = VectorStore()
if 'rag_system' not in st.session_state:
    st.session_state.rag_system = RAGSystem()

# Page configuration
st.set_page_config(
    page_title="Multi-Document RAG System",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Context-Aware Multi-Document RAG System")
st.markdown("Upload multiple documents and get AI-powered summaries and answers to your questions.")

# Check for OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("⚠️ OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

# Sidebar for document management
with st.sidebar:
    st.header("📁 Document Management")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Documents",
        type=['pdf', 'txt', 'docx'],
        accept_multiple_files=True,
        help="Upload PDF, TXT, or DOCX files"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state.documents:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    try:
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_file_path = tmp_file.name
                        
                        # Process document
                        doc_processor = DocumentProcessor()
                        content = doc_processor.extract_content(tmp_file_path, uploaded_file.type)
                        chunks = doc_processor.chunk_text(content)
                        
                        # Create embeddings and store
                        embeddings = st.session_state.vector_store.create_embeddings(chunks)
                        doc_id = st.session_state.vector_store.add_document(uploaded_file.name, chunks, embeddings)
                        
                        # Store document info
                        st.session_state.documents[uploaded_file.name] = {
                            'id': doc_id,
                            'content': content,
                            'chunks': len(chunks),
                            'size': len(content)
                        }
                        
                        # Clean up temporary file
                        os.unlink(tmp_file_path)
                        
                        st.success(f"✅ {uploaded_file.name} processed successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
                        # Clean up temporary file if it exists
                        try:
                            if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                                os.unlink(tmp_file_path)
                        except:
                            pass
    
    # Display uploaded documents
    if st.session_state.documents:
        st.subheader("📋 Uploaded Documents")
        for doc_name, doc_info in st.session_state.documents.items():
            with st.expander(f"📄 {doc_name}"):
                st.write(f"**Chunks:** {doc_info['chunks']}")
                st.write(f"**Size:** {doc_info['size']:,} characters")
                
                if st.button(f"Delete {doc_name}", key=f"delete_{doc_name}"):
                    st.session_state.vector_store.remove_document(doc_info['id'])
                    del st.session_state.documents[doc_name]
                    st.rerun()

# Main content area
if not st.session_state.documents:
    st.info("👆 Please upload some documents to get started!")
else:
    # Tabs for different functionalities
    tab1, tab2 = st.tabs(["📝 Document Summaries", "💬 Ask Questions"])
    
    with tab1:
        st.header("📝 Document Summaries")
        
        if st.button("Generate Summaries for All Documents", type="primary"):
            with st.spinner("Generating summaries..."):
                try:
                    summaries = {}
                    for doc_name, doc_info in st.session_state.documents.items():
                        summary = st.session_state.rag_system.summarize_document(doc_info['content'])
                        summaries[doc_name] = summary
                    
                    st.session_state.summaries = summaries
                    st.success("✅ Summaries generated successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error generating summaries: {str(e)}")
        
        # Display summaries if available
        if hasattr(st.session_state, 'summaries'):
            for doc_name, summary in st.session_state.summaries.items():
                with st.expander(f"📋 Summary: {doc_name}", expanded=True):
                    st.write(summary)
    
    with tab2:
        st.header("💬 Ask Questions About Your Documents")
        
        # Chat interface
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Display chat history
        for i, (question, answer) in enumerate(st.session_state.chat_history):
            with st.container():
                st.write("**🙋 You:**", question)
                st.write("**🤖 Assistant:**", answer)
                st.divider()
        
        # Question input
        question = st.text_input("Ask a question about your documents:", key="question_input")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            ask_button = st.button("Ask", type="primary")
        with col2:
            if st.button("Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()
        
        if ask_button and question:
            with st.spinner("Searching for relevant information and generating answer..."):
                try:
                    # Retrieve relevant context
                    relevant_chunks = st.session_state.vector_store.similarity_search(question, top_k=5)
                    
                    if not relevant_chunks:
                        st.warning("No relevant information found in the uploaded documents.")
                    else:
                        # Generate answer using RAG
                        answer = st.session_state.rag_system.answer_question(question, relevant_chunks)
                        
                        # Add to chat history
                        st.session_state.chat_history.append((question, answer))
                        
                        # Clear input and rerun to show new message
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error answering question: {str(e)}")

# Footer
st.markdown("---")
st.markdown("**Note:** This system uses OpenAI's GPT-4o and embedding models to provide intelligent document analysis and question answering.")
