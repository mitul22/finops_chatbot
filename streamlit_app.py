import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
from home_page import page_setup
from typing import Dict, List, Optional, Tuple, Union
import time
import _snowflake 
import json

# Connect Snowpark 
session = get_active_session()
API_ENDPOINT = "/api/v2/cortex/analyst/message"
FEEDBACK_ENDPOINT = "/api/v2/cortex/analyst/feedback"
API_TIMEOUT = 60000
SEMANTIC_VIEW ='development.finops_billrun.invoice_sm_vw'

# Initialize session states 
if "messages" not in st.session_state:
    st.session_state.messages = []
if "awaiting_response" not in st.session_state:
    st.session_state.awaiting_response = False
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = ({})
    
def chat_input():
    user_question = st.chat_input('Ask anything about invoices...')
    if user_question:
        process_chat_input(user_question)

def display_message(
    content: List[Dict[str, Union[str, Dict]]],
    message_index: int,
    request_id: Union[str, None] = None,
):
    """
    Display raw message content for inspection.
    """
    st.write("**Raw Content Structure:**")
    st.json(content)
    
    st.write("**Message Index:**", message_index)
    if request_id:
        st.write("**Request ID:**", request_id)
    
    # Show each item type
    for idx, item in enumerate(content):
        st.write(f"--- Item {idx} ---")
        st.write(f"**Type:** `{item.get('type')}`")
        st.json(item)

def process_chat_input(user_question):
    # Queue the new question and add it to history. Display the question
    new_user_message = {
        "role": "user",
        "content": [{"type": "text", "text": user_question}],
    }
    st.session_state.messages.append(new_user_message)
    with st.chat_message("user"):
        st.write(user_question)

    with st.chat_message("analyst"):
        with st.spinner("Waiting for Analyst's response..."):
            time.sleep(2)
            response, error_msg = post_question_cortex(st.session_state.messages)
                 
            if error_msg is None:
                analyst_message = {
                    "role": "analyst",
                    "content": response["message"]["content"],
                    "request_id": response["request_id"],
                    "raw_response": response  # Store full response for inspection
                }
            else:
                analyst_message = {
                    "role": "analyst",
                    "content": [{"type": "text", "text": error_msg}],
                    "request_id": response.get("request_id"),
                    "raw_response": response,
                    "error": True
                }
                st.session_state["fire_API_error_notify"] = True

            if "warnings" in response:
                st.session_state.warnings = response["warnings"]
                st.warning(f"⚠️ Warnings: {response['warnings']}")

            st.session_state.messages.append(analyst_message)
            st.rerun()

def handle_error_notifications():
    if st.session_state.get("fire_API_error_notify"):
        st.toast("An API error has occured!", icon="🚨")
        st.session_state["fire_API_error_notify"] = False

# display only the text and output of the SQL
def structure_output(raw_response: dict, message_index: int):
    if "message" in raw_response and "content" in raw_response["message"]:
        content_items = raw_response["message"]["content"]
        
        for idx, item in enumerate(content_items):
            item_type = item.get("type")
            
            if item_type == "text":
                st.markdown(item.get("text", ""))
            
            elif item_type == "sql":
                try:
                    result_df = session.sql(item.get("statement", "")).to_pandas()
                    st.dataframe(result_df, use_container_width=True)
                    if "confidence" in item: 
                        confidence = item.get('confidence', {})
                        verified_query = confidence.get('verified_query_used')
                        if verified_query is None:
                            st.caption("Confidence: Moderate - Verified Query was not used")
                        else:
                            st.caption(f"Confidence: High - Verified Query was used for this answer")
                
                except Exception as e:
                    st.error(f"Error retrieving data: {e}")
    
    if "request_id" in raw_response:
        rate_output(raw_response["request_id"])

    
    if "warnings" in raw_response and raw_response["warnings"]:
        st.warning(f" {raw_response['warnings']}")
    
def display_conversation_history():
    """Display all messages from the conversation history."""
    for message_index, message in enumerate(st.session_state.messages):
        role = message["role"]
        with st.chat_message(role):
            if role == "user":
                # Simple display for user messages
                st.write(message["content"][0]["text"])
            else:

                # Show only the intrepretation and final output
                if "raw_response" in message:
                    structure_output(message["raw_response"], message_index)
                

def post_question_cortex(messages: List[Dict]) -> Tuple[Dict, Optional[str]]:
    request_body = {"messages": messages, "semantic_view": SEMANTIC_VIEW,}

    # Make an API call to Cortex AI
    resp = _snowflake.send_snow_api_request("POST", API_ENDPOINT, {}, {}, request_body, None, API_TIMEOUT,)

    parsed_content = json.loads(resp["content"])

    if resp["status"] == 200:
        return parsed_content, None
    else:
        error_msg = f"""
        🚨 robot down! robot down!  🚨
        
        * response code: `{resp['status']}`
        
        Message:
        ```
        {parsed_content.get('message', 'No error message')}
        ```
        """
    return parsed_content, error_msg

def rate_output(request_id: str):
    with st.popover("Rate the answer"):
        if request_id not in st.session_state.form_submitted:
            with st.form(f"feedback_form_{request_id}", clear_on_submit=True):
                rating = st.radio(
                    "Rate the answer", options=["Great", "Could be better", "Wrong"]
                )
                rating = rating == "Great"
                submit_disabled = (
                    request_id in st.session_state.form_submitted
                    and st.session_state.form_submitted[request_id]
                )

                feedback_message = st.text_input("Additional feedback")
                submitted = st.form_submit_button("Submit", disabled=submit_disabled)
                if submitted:
                    err_msg = post_feedback(request_id, rating, feedback_message)
                    st.session_state.form_submitted[request_id] = {"error": err_msg}
                    st.session_state.popover_open = False
                    st.rerun()
        elif (
            request_id in st.session_state.form_submitted
            and st.session_state.form_submitted[request_id]["error"] is None
        ):
            st.success("Feedback submitted", icon="✅")
        else:
            st.error(st.session_state.form_submitted[request_id]["error"])

def post_feedback(request_id: str, positive: bool, feedback_message: str) -> Optional[str]:
    
    request_body = {"request_id": request_id, "positive": positive, "feedback_message": feedback_message,}
    
    resp = _snowflake.send_snow_api_request("POST", FEEDBACK_ENDPOINT, {}, {}, request_body, None, API_TIMEOUT,)

    if not resp.get("content"):
        if resp.get("status") == 200:
            return None
        parsed_content = {}
    else:
        try:
            parsed_content = json.loads(resp["content"])
        except json.JSONDecodeError as e:
            return f"🚨 API returned invalid JSON content. Status: {resp.get('status')}. Error: {e}"

    if resp["status"] == 200:
        return None

    else:
        error_msg = f"""
        🚨 robot down! robot down! 🚨
        
        * response code: `{resp['status']}`
        
        Message:
        ```
        {parsed_content.get('message', 'No error message')}
        ```
        """
    return error_msg

def main():
    page_setup()
      
    display_conversation_history()
    chat_input()

if __name__ == "__main__":
    main()