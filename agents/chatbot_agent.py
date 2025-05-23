from enum import Enum
from dataclasses import dataclass
from typing import Optional
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.chains import RetrievalQA
from config.settings import get_llm_model
from utils.document_processor import DocumentProcessor
from utils.validators import Validators
from tools.booking import book_appointment_tool
from tools.user_input import validate_user_input_tool

class ConversationState(Enum):
    GENERAL = "general"
    COLLECTING_INFO = "collecting_info"
    BOOKING_APPOINTMENT = "booking_appointment"

@dataclass
class UserInfo:
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    appointment_date: Optional[str] = None

class ChatbotAgent:
    def __init__(self):
        self.llm = get_llm_model()
        self.doc_processor = DocumentProcessor()
        self.vectorstore = None
        self.qa_chain = None
        self.tools = [book_appointment_tool, validate_user_input_tool]
        self.agent_executor = self._create_agent()
    
    def _create_agent(self):
        """Create the agent with tools"""
        system_message = """You are an intelligent assistant that can:
1. Answer questions from uploaded documents
2. Help users book appointments by collecting their information
3. Validate user inputs (email, phone, dates)

When a user asks to "call them" or "book an appointment", initiate the information collection process.
Always validate user inputs and provide helpful feedback.
Extract dates in YYYY-MM-DD format from natural language (e.g., "next Monday" → "2024-12-23").

Be conversational and helpful. Guide users through the process step by step.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)
    
    def load_documents(self, uploaded_files):
        """Load and process documents"""
        self.vectorstore = self.doc_processor.process_documents(uploaded_files)
        if self.vectorstore:
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
                return_source_documents=False
            )
            return True
        return False
    
    def get_response(self, query: str, user_info: UserInfo, conversation_state: ConversationState) -> tuple:
        """Get response from the chatbot"""
        
        # Check if user is asking to book appointment or call
        call_keywords = ['call me', 'book appointment', 'schedule appointment', 'book a call', 'contact me']
        if any(keyword in query.lower() for keyword in call_keywords):
            conversation_state = ConversationState.COLLECTING_INFO
            return "I'd be happy to help you book an appointment! Let me collect some information from you. What's your full name?", conversation_state
        
        # Handle information collection state
        if conversation_state == ConversationState.COLLECTING_INFO:
            return self._handle_info_collection(query, user_info)
        
        # Try to answer from documents first
        if self.qa_chain:
            try:
                doc_response = self.qa_chain.run(query)
                if doc_response and "I don't know" not in doc_response:
                    return doc_response, conversation_state
            except Exception as e:
                st.error(f"Error querying documents: {str(e)}")
        
        # Use agent for general queries
        try:
            response = self.agent_executor.invoke({"input": query})
            return response.get("output", "I'm sorry, I couldn't process your request."), conversation_state
        except Exception as e:
            return f"I encountered an error: {str(e)}", conversation_state
    
    def _handle_info_collection(self, query: str, user_info: UserInfo) -> tuple:
        """Handle the information collection process"""
        
        # Determine what information we're collecting
        if not user_info.name:
            user_info.name = query.strip()
            return "Great! Now, could you please provide your phone number?", ConversationState.COLLECTING_INFO
        
        elif not user_info.phone:
            if Validators.validate_phone(query):
                user_info.phone = query.strip()
                return "Perfect! Now, please provide your email address.", ConversationState.COLLECTING_INFO
            else:
                return "Please provide a valid phone number (e.g., +91XXXXXXXXXX or 10-digit number).", ConversationState.COLLECTING_INFO
        
        elif not user_info.email:
            if Validators.validate_email(query):
                user_info.email = query.strip()
                return "Excellent! Finally, when would you like to schedule the appointment? (e.g., 'next Monday', 'tomorrow', or '2024-12-25')", ConversationState.COLLECTING_INFO
            else:
                return "Please provide a valid email address (e.g., user@example.com).", ConversationState.COLLECTING_INFO
        
        elif not user_info.appointment_date:
            parsed_date = Validators.parse_date_from_text(query)
            if parsed_date:
                user_info.appointment_date = parsed_date
                
                # Book the appointment using the tool
                booking_result = book_appointment_tool.invoke({
                    'name': user_info.name,
                    'phone': user_info.phone,
                    'email': user_info.email,
                    'appointment_date': user_info.appointment_date
                })
                
                # Reset user info for next interaction
                user_info.name = None
                user_info.phone = None
                user_info.email = None
                user_info.appointment_date = None
                
                return booking_result, ConversationState.GENERAL
            else:
                return "I couldn't understand the date. Please specify when you'd like to book (e.g., 'next Monday', 'tomorrow', or '2024-12-25').", ConversationState.COLLECTING_INFO
        
        return "Thank you for the information!", ConversationState.GENERAL
