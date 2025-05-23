import os
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from dotenv import load_dotenv
import streamlit as st
from agents.chatbot_agent import ChatbotAgent, UserInfo, ConversationState


def main():
    st.set_page_config(
        page_title="AI Chatbot Assistant",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 AI Chatbot Assistant")
    st.markdown("---")
    
    # Initialize session state
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = ChatbotAgent()
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'user_info' not in st.session_state:
        st.session_state.user_info = UserInfo()
    if 'conversation_state' not in st.session_state:
        st.session_state.conversation_state = ConversationState.GENERAL
    
    # Sidebar for document upload
    with st.sidebar:
        st.header("📄 Document Upload")
        uploaded_files = st.file_uploader(
            "Upload documents (PDF, DOCX, TXT)",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Upload documents that the chatbot can reference to answer your questions."
        )

        # Auto-process when new files are uploaded
        if uploaded_files:
            # ensure we only process once per session or when files change
            uploaded_names = [f.name for f in uploaded_files]
            if st.session_state.get('last_uploaded_names') != uploaded_names:
                st.session_state.last_uploaded_names = uploaded_names
                with st.spinner("Processing documents..."):
                    success = st.session_state.chatbot.load_documents(uploaded_files)
                    if success:
                        st.success(f"Successfully processed {len(uploaded_files)} document(s)!")
                    else:
                        st.error("Failed to process documents. Please try again.")

        st.markdown("---")
        st.header("ℹ️ Features")
        st.markdown("""
        - **Document Q&A**: Upload documents and ask questions
        - **Appointment Booking**: Say "call me" or "book appointment"
        - **Smart Validation**: Email, phone, and date validation
        - **Natural Language**: Understands "next Monday", "tomorrow", etc.
        """
        )
        
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.session_state.user_info = UserInfo()
            st.session_state.conversation_state = ConversationState.GENERAL
            st.session_state.last_uploaded_names = []
            st.rerun()
    
    # Main chat interface
    st.header("💬 Chat Interface")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("Ask me anything or say 'call me' to book an appointment..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response, new_state = st.session_state.chatbot.get_response(
                    prompt, 
                    st.session_state.user_info, 
                    st.session_state.conversation_state
                )
                st.session_state.conversation_state = new_state
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    if st.session_state.conversation_state != ConversationState.GENERAL:
        st.info(f"Current state: {st.session_state.conversation_state.value}")
        info_display = []
        if st.session_state.user_info.name:
            info_display.append(f"Name: {st.session_state.user_info.name}")
        if st.session_state.user_info.phone:
            info_display.append(f"Phone: {st.session_state.user_info.phone}")
        if st.session_state.user_info.email:
            info_display.append(f"Email: {st.session_state.user_info.email}")
        if st.session_state.user_info.appointment_date:
            info_display.append(f"Date: {st.session_state.user_info.appointment_date}")
        if info_display:
            st.info("Collected Information: " + " | ".join(info_display))

if __name__ == "__main__":
    main()
