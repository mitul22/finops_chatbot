import streamlit as st


def page_setup():
    st.set_page_config(
        page_title="FinOps Chatbot",
        page_icon="🤖",
        layout="centered",
    )

    # Header
    st.title("🤖 FinOps Chatbot")
    st.markdown("v0.1 - Agentic AI for Self-Serve Analytics")
    st.divider()

    st.subheader("💡 Suggested Questions")

    example_questions = [
        "What's the revenue in October 2025 compared to September 2025?",
        "Which product group had the largest percentage change in revenue from September 2025 to October 2025?",
        "How many subscriptions billed in September 2025 were not billed in October 2025?",
        "Show me top 10 customers by revenue in October 2025",
        "What's the month-over-month revenue growth trend for Q4 2025?",
    ]

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
                # If a user clicks the suggested question, add it to the queue
                st.session_state.messages.append({
                    "role": "user", 
                    "content": question
                })
                st.session_state.awaiting_response = True
                st.rerun()
    
    st.divider()
    
    #Footer
    st.caption("💡 Tip: Be specific in your questions for better results. Include date ranges and metrics you want to analyze.") 