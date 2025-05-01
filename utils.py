import yaml
import streamlit as st
from streamlit_lottie import st_lottie
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_yaml_config(file_path='config.yaml'):
    try:
        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)
        logger.debug(f"Loaded config from {file_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config from {file_path}: {e}")
        raise Exception(f"Failed to load config: {e}")

def load_lottie_animation(url):
    try:
        logger.debug(f"Fetching Lottie animation from {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        lottie_json = response.json()
        st_lottie(lottie_json, height=200, key=f"lottie_{url}")
        logger.debug("Lottie animation loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Lottie animation: {e}")
        st.warning(f"Failed to load animation: {e}")