# generate_hashes.py
from streamlit_authenticator import Hasher

passwords = ['password123']
hashes = Hasher(passwords).generate()
for pwd, h in zip(passwords, hashes):
    print(f"Password: {pwd}, Hash: {h}")