import httpx
import streamlit as st
from supabase import create_client, Client, ClientOptions


@st.cache_resource
def get_supabase() -> Client:
    http_client = httpx.Client(verify=False, timeout=120.0)
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
        options=ClientOptions(httpx_client=http_client),
    )
