import pytest
from core.authentication import AuthenticationManager

def test_generate_jwt():
    auth = AuthenticationManager('test-secret', 24)
    user_info = {'email': 'test@example.com', 'name': 'Test'}
    
    token = auth.generate_jwt(user_info)
    
    assert token is not None
    assert isinstance(token, str)

def test_verify_jwt():
    auth = AuthenticationManager('test-secret', 24)
    user_info = {'email': 'test@example.com'}
    
    token = auth.generate_jwt(user_info)
    payload = auth.verify_jwt(token)
    
    assert payload is not None
    assert payload['user']['email'] == 'test@example.com'
