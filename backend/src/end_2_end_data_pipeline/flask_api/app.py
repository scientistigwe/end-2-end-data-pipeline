# app.py
from flask import Flask, request, jsonify
from Crypto.Cipher import AES
import base64
import json

app = Flask(__name__)


# Encryption utility
def encrypt_credentials(credentials):
    key = b'Sixteen byte key'  # Secret key for AES encryption
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(credentials).encode())
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode()


# API to receive and store credentials
@app.route('/api/stream-source', methods=['POST'])
def configure_stream_source():
    data = request.get_json()
    source_type = data['sourceType']
    credentials = data['credentials']

    encrypted_credentials = encrypt_credentials(credentials)

    # Here you can save the encrypted credentials securely (e.g., database or file)
    # For simplicity, we are returning them as a response (just for demonstration).

    return jsonify({
        'status': 'success',
        'encryptedCredentials': encrypted_credentials
    })


if __name__ == '__main__':
    app.run(debug=True)
