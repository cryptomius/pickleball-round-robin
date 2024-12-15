from setuptools import setup, find_packages

setup(
    name="pickleball",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "pandas",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "extra_streamlit_components",
    ],
)
