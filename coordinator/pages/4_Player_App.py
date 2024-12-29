import streamlit as st
import qrcode
from io import BytesIO
import PIL.Image

PLAYER_APP_URL = 'https://pickleball-tournament.streamlit.app/'

# Force light theme
st.set_page_config(page_title="Player App", layout="wide", initial_sidebar_state="collapsed")

st.title("Player App")

# Add custom CSS and JavaScript for copy functionality
st.markdown("""
    <style>
    .block-container {
        padding: 1.5rem 1.4rem !important;
    }
    .appview-container section:first-child {
        width: 250px !important;
    }
    .stTextInput button {
        margin-left: 0.5rem;
    }
    </style>
    <script>
    function copyUrl() {
        navigator.clipboard.writeText('""" + PLAYER_APP_URL + """');
    }
    </script>
""", unsafe_allow_html=True)

# Create QR code
qr = qrcode.QRCode(version=1, box_size=10, border=5)
qr.add_data(PLAYER_APP_URL)
qr.make(fit=True)

# Create PIL image
qr_image = qr.make_image(fill_color="black", back_color="white")

# Convert PIL image to bytes
img_byte_arr = BytesIO()
qr_image.save(img_byte_arr, format='PNG')
img_byte_arr = img_byte_arr.getvalue()

# Display QR code
st.image(img_byte_arr)

# Add URL in a copyable field and note
st.code(PLAYER_APP_URL, language=None)
st.write("Let someone scan this code to view the player app")
