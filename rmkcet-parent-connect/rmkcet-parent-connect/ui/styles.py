# ui/styles.py
"""Custom CSS and header for the futuristic theme."""
import streamlit as st


def load_custom_css():
    """Inject global custom CSS."""
    st.markdown("""
    <style>
    /* === Global === */
    .stApp {
        background: radial-gradient(circle at 20% 20%, #1a1f2e, #0a0c14);
        color: #ffffff;
    }
    section[data-testid="stSidebar"] {
        background: rgba(10, 12, 20, 0.95);
        border-right: 1px solid rgba(102, 126, 234, 0.2);
    }

    /* === Cards === */
    .glass-card {
        background: rgba(20, 30, 50, 0.7);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(102, 126, 234, 0.15);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        border-color: rgba(102, 126, 234, 0.4);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
    }

    /* === Metric Cards === */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #cbd5e1;
        margin-top: 0.3rem;
    }

    /* === Status Badges === */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-active { background: rgba(37, 211, 102, 0.2); color: #25D366; }
    .badge-locked { background: rgba(231, 76, 60, 0.2); color: #e74c3c; }
    .badge-inactive { background: rgba(203, 213, 225, 0.2); color: #cbd5e1; }
    .badge-admin { background: rgba(243, 156, 18, 0.2); color: #f39c12; }
    .badge-counselor { background: rgba(102, 126, 234, 0.2); color: #667eea; }
    .badge-idle { background: rgba(243, 156, 18, 0.2); color: #f39c12; }

    /* === Buttons === */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }

    /* === Tabs === */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(20, 30, 50, 0.5);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        color: #cbd5e1;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
    }

    /* === Inputs === */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
        background: rgba(20, 30, 50, 0.8);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 10px;
        color: white;
    }

    /* === Expander === */
    .streamlit-expanderHeader {
        background: rgba(20, 30, 50, 0.5);
        border-radius: 10px;
    }

    /* === Session Timer === */
    .session-timer {
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0,0,0,0.8);
        backdrop-filter: blur(10px);
        padding: 8px 16px;
        border-radius: 24px;
        color: white;
        font-size: 0.9rem;
        font-weight: 500;
        border: 2px solid #667eea;
        z-index: 999;
        box-shadow: 0 0 20px rgba(102,126,234,0.3);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { border-color: #667eea; }
        50% { border-color: #764ba2; }
    }

    /* === Table === */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }

    /* === Scrollbar === */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0c14; }
    ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)


def college_header():
    """Render the college header / branding."""
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
        <h1 style="margin:0; background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                    font-size: 2.2rem;">
            🎓 RMKCET Parent Connect
        </h1>
        <p style="color: #cbd5e1; font-size: 0.9rem; margin-top:0.3rem;">
            Academic Progress Monitoring System
        </p>
    </div>
    """, unsafe_allow_html=True)


def metric_card(label: str, value, icon: str = "📊"):
    """Render a styled metric card."""
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:1.5rem;">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def status_badge(text: str, variant: str = "active"):
    """Return HTML for a status badge."""
    return f'<span class="badge badge-{variant}">{text}</span>'
