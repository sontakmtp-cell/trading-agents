import unittest
from unittest.mock import patch
import pytest
import questionary

from cli.utils import ask_output_language, select_openrouter_model


@pytest.mark.unit
class TestCliChoices(unittest.TestCase):
    @patch("questionary.select")
    def test_ask_output_language_includes_vietnamese(self, mock_select):
        # Mock the ask method on the returned select object to return a value
        mock_select.return_value.ask.return_value = "English"

        ask_output_language()

        mock_select.assert_called_once()
        kwargs = mock_select.call_args[1]
        choices = kwargs.get("choices", [])
        
        # Check that Vietnamese is in the choices list
        vietnamese_choice = next((c for c in choices if c.value == "Vietnamese"), None)
        self.assertIsNotNone(vietnamese_choice)
        self.assertEqual(vietnamese_choice.title, "Vietnamese (Tiếng Việt)")

    @patch("cli.utils._fetch_openrouter_models")
    @patch("questionary.select")
    def test_select_openrouter_model_includes_deepseek_models(self, mock_select, mock_fetch):
        # Mock fetch_openrouter_models to return some dynamic models
        mock_fetch.return_value = [("Dynamic Model 1", "dynamic/model-1")]
        # Mock the ask method on the select prompt to return one of the deepseek models
        mock_select.return_value.ask.return_value = "deepseek/deepseek-v4-pro"

        selected = select_openrouter_model()

        self.assertEqual(selected, "deepseek/deepseek-v4-pro")
        mock_select.assert_called_once()
        kwargs = mock_select.call_args[1]
        choices = kwargs.get("choices", [])

        # Check deepseek choices
        ds_pro = next((c for c in choices if c.value == "deepseek/deepseek-v4-pro"), None)
        self.assertIsNotNone(ds_pro)
        self.assertEqual(ds_pro.title, "DeepSeek V4 Pro (deepseek/deepseek-v4-pro)")

        ds_flash = next((c for c in choices if c.value == "deepseek/deepseek-v4-flash"), None)
        self.assertIsNotNone(ds_flash)
        self.assertEqual(ds_flash.title, "DeepSeek V4 Flash (deepseek/deepseek-v4-flash)")

        # Check that fetched dynamic model is also present
        dynamic_model = next((c for c in choices if c.value == "dynamic/model-1"), None)
        self.assertIsNotNone(dynamic_model)
        self.assertEqual(dynamic_model.title, "Dynamic Model 1")
