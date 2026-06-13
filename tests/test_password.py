import unittest
from src.security.password import PasswordPolicy, PasswordHasherService

class TestPasswordPolicy(unittest.TestCase):
    def test_validate_strong_password(self):
        valid, errors = PasswordPolicy.validate('Abc123!@#')
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_weak_passwords(self):
        valid, errors = PasswordPolicy.validate('weak')
        self.assertFalse(valid)
        self.assertIn('密码长度至少8位', errors)
        
        valid, errors = PasswordPolicy.validate('weakpassword')
        self.assertFalse(valid)
        self.assertIn('需要包含大写字母', errors)
        self.assertIn('需要包含数字', errors)
        self.assertIn('需要包含特殊字符', errors)
    
    def test_calculate_strength(self):
        score, label = PasswordPolicy.calculate_strength('weak')
        self.assertEqual(score, 2)
        self.assertEqual(label, '弱')
        
        score, label = PasswordPolicy.calculate_strength('Abc123!@#')
        self.assertEqual(score, 6)
        self.assertEqual(label, '非常强')

class TestPasswordHasher(unittest.TestCase):
    def setUp(self):
        self.hasher = PasswordHasherService()
    
    def test_hash_and_verify(self):
        password = 'Abc123!@#'
        hashed = self.hasher.hash_password(password)
        
        self.assertTrue(self.hasher.verify_password(hashed, password))
        self.assertFalse(self.hasher.verify_password(hashed, 'wrong_password'))
    
    def test_hash_format(self):
        password = 'Abc123!@#'
        hashed = self.hasher.hash_password(password)
        
        self.assertTrue(hashed.startswith('$argon2id$'))

if __name__ == '__main__':
    unittest.main()
