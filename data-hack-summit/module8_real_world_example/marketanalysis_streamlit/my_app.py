import streamlit as st
from market_analysis import run_market_analysis_feedback_loop
from dotenv import load_dotenv

load_dotenv()

# Set page title
st.set_page_config(page_title="SWOT Analysis Chat", layout="wide")

# Main title
st.title("SWOT Analysis")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input at the bottom
if prompt := st.chat_input("Ask me about SWOT analysis..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response (placeholder for now)
    with st.chat_message("assistant"):
        response = run_market_analysis_feedback_loop(prompt)
        st.markdown(response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
