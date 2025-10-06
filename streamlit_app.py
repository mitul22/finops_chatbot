import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import json 
import time 
from datetime import datetime 
from typing import Dict, List, Optional, Tuple, Union
from page_layout import print_times

# Connect Snowpark 
session = get_active_session()

semantic_view = 'development.finops_billrun.invoices_sm_vw'

API_ENDPOINT = "/api/v2/cortex/analyst/message"
FEEDBACK_API_ENDPOINT = "/api/v2/cortex/analyst/feedback"
API_TIMEOUT = 50000  # in milliseconds

# Setup the page laout
st.set_page_config(
    page_title="FinOps Chatbot",
    page_icon="🤖",
    layout="centered",
)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "awaiting_response" not in st.session_state:
    st.session_state.awaiting_response = False

# Header
st.title("🤖 FinOps Chatbot")
st.caption(print_times())
st.caption("v0.1 - Agentic AI for Self-Serve Analytics")
st.divider()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display dataframe if present
        if "dataframe" in message:
            st.dataframe(message["dataframe"], use_container_width=True)
        
        # Display chart if present
        if "chart" in message:
            st.plotly_chart(message["chart"], use_container_width=True)

# Process pending responses
if st.session_state.awaiting_response:
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your question..."):
            last_message = st.session_state.messages[-1]["content"]
            
            # Placeholder response logic
            response = process_user_query(session, last_message)
            
            st.markdown(response["text"])
            
            if "dataframe" in response and response["dataframe"] is not None:
                st.dataframe(response["dataframe"], use_container_width=True)
            
            if "chart" in response and response["chart"] is not None:
                st.plotly_chart(response["chart"], use_container_width=True)
            
            # Add response to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response["text"],
                "dataframe": response.get("dataframe"),
                "chart": response.get("chart")
            })
            
            st.session_state.awaiting_response = False
            st.rerun()


# Example questions section
st.subheader("💡 Suggested Questions")

example_questions = [
    "What's the revenue in October 2025 compared to September 2025?",
    "Which product group had the largest percentage change in revenue from September 2025 to October 2025?",
    "How many subscriptions billed in September 2025 were not billed in October 2025?",
    "Show me top 10 customers by revenue in October 2025",
    "What's the month-over-month revenue growth trend for Q4 2025?",
]

# Display example questions as buttons in columns
cols = st.columns(2)
for idx, question in enumerate(example_questions):
    col = cols[idx % 2]
    with col:
        if st.button(
            question, 
            key=f"example_q_{idx}",
            use_container_width=True,
            disabled=st.session_state.awaiting_response
        ):
            # Add user message
            st.session_state.messages.append({
                "role": "user", 
                "content": question
            })
            st.session_state.awaiting_response = True
            st.rerun()

st.divider()

# Chat input at the bottom
if prompt := st.chat_input(
    "Ask anything about invoices...",
    disabled=st.session_state.awaiting_response
):
    # Add user message
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt
    })
    st.session_state.awaiting_response = True
    st.rerun()


def process_user_query(session, query: str) -> dict:
    """
    Process user query and return response
    
    Args:
        session: Snowflake session
        query: User's question
    
    Returns:
        dict with 'text', optional 'dataframe', and optional 'chart'
    """
    # TODO: Implement your actual query processing logic here
    # This should include:
    # 1. Natural language to SQL conversion (using Cortex or similar)
    # 2. Query execution
    # 3. Result formatting
    # 4. Chart generation if applicable
    
    # Placeholder implementation
    try:
        # Example query execution
        # result = session.sql("SELECT * FROM INVOICES LIMIT 10").to_pandas()
        
        response = {
            "text": "I'm processing your question. Please implement the backend logic in `process_user_query()`.",
            # "dataframe": result,  # Optional pandas dataframe
            # "chart": fig  # Optional plotly figure
        }
        return response
        
    except Exception as e:
        return {
            "text": f"❌ Error processing your request: {str(e)}"
        }


# Footer
st.caption("💡 Tip: Be specific in your questions for better results. Include date ranges and metrics you want to analyze.")