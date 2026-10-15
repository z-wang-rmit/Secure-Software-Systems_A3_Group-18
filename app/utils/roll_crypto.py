# Protecting electoral roll personal details
# PLACEHOLDER (R06): no encryption yet. R06 uses AES-256-GCM (Week 2 EncryptionUtil).


def encrypt_field(value):
    """str -> bytes stored in the database"""
    return value.encode('utf-8')


def decrypt_field(data):
    """bytes from the database -> str"""
    return data.decode('utf-8')
