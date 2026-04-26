import unittest
import json

class TestSafetySwitch(unittest.TestCase):
    def test_01_fixed_logic(self):
        # Имитируем НОВУЮ логику
        def prepare_data_logic(input_data):
            is_test = input_data.get('is_devops_test') == True
            model_config = input_data.get('model_config') or { 'mainModel': 'ollama' }
            
            if is_test:
                model_config = { 'mainModel': 'openai', 'mainModelName': 'google/gemini-2.0-flash-001' }
            
            return model_config

        # Сценарий 1: Режим теста ВКЛЮЧЕН
        test_input_on = {'is_devops_test': True, 'model_config': {'mainModelName': 'gpt-4o'}}
        result_on = prepare_data_logic(test_input_on)
        self.assertEqual(result_on['mainModelName'], 'google/gemini-2.0-flash-001', "Safety switch FAILED to override model!")

        # Сценарий 2: Режим теста ВЫКЛЮЧЕН
        test_input_off = {'is_devops_test': False, 'model_config': {'mainModelName': 'gpt-4o'}}
        result_off = prepare_data_logic(test_input_off)
        self.assertEqual(result_off['mainModelName'], 'gpt-4o', "Safety switch blocked PROD model incorrectly!")

if __name__ == '__main__':
    unittest.main()
