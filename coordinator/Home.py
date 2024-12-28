import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import qrcode
import io

st.set_page_config(
    page_title="Home - Pickleball Round Robin",
    page_icon="🏸",
    layout="wide",
)


# Add custom CSS
st.markdown("""
    <style>
    .block-container {
        padding: 1.5rem 1.4rem !important;
    }
    .appview-container section:first-child {
        width: 250px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Pickleball Round Robin - Coordinator")
st.write("Welcome to the Pickleball Round Robin Tournament Management System!")
st.write("Please use the sidebar to navigate between different sections:")
st.write("1. **Player Management**: Add new players and manage player status")
st.write("2. **Match Management**: Generate matches, submit scores, and view court status")
st.write("3. **Tournament Summary**: View tournament statistics and current standings")

# Add QR code section
st.markdown("---")
st.subheader("Quick Access")
st.write("Scan this code to open the coordinator app on another device:")

# Generate QR code for the current page URL
qr = qrcode.QRCode(version=1, box_size=10, border=5)
current_url = "https://pickleball-coordinator.streamlit.app/"
qr.add_data(current_url)
qr.make(fit=True)

# Create the QR code image
img = qr.make_image(fill_color="black", back_color="white")

# Convert PIL image to bytes
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_byte_arr = img_byte_arr.getvalue()

# Create columns for centered display
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Display the QR code
    st.image(img_byte_arr)
    # Display the URL
    st.code(current_url, language="text")
