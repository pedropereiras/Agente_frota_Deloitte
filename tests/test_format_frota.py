import unittest
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, ToolMessage

from src.graph.nodes.format_frota import format_frota


class FormatFrotaTests(unittest.TestCase):
    def test_keeps_existing_answer_without_an_extra_model_call(self):
        state = {
            "pergunta": "Qual navio chega primeiro?",
            "messages": [
                ToolMessage(
                    content="[relatorio_frota#S3-CORAL] dados",
                    name="consultar_frota",
                    tool_call_id="call-1",
                ),
                AIMessage(content="S3-CORAL chega primeiro."),
            ],
        }

        with patch("src.utils.llm_adapter.get_llm") as get_llm:
            result = format_frota(state)

        self.assertIn("S3-CORAL chega primeiro.", result["resultado"])
        self.assertIn("relatorio_frota#S3-CORAL", result["resultado"])
        get_llm.assert_not_called()

    def test_generates_final_answer_when_last_message_is_empty(self):
        state = {
            "pergunta": "Qual navio chega primeiro?",
            "messages": [
                ToolMessage(
                    content="[relatorio_frota#S3-CORAL] dados",
                    name="consultar_frota",
                    tool_call_id="call-1",
                ),
                AIMessage(content=""),
            ],
        }
        llm = Mock()
        llm.invoke.return_value = AIMessage(content="S3-CORAL chega primeiro.")

        with patch("src.utils.llm_adapter.get_llm", return_value=llm):
            result = format_frota(state)

        self.assertIn("S3-CORAL chega primeiro.", result["resultado"])
        self.assertIn("relatorio_frota#S3-CORAL", result["resultado"])
        llm.invoke.assert_called_once()

    def test_raises_when_final_answer_remains_empty(self):
        state = {
            "pergunta": "Qual navio chega primeiro?",
            "messages": [
                ToolMessage(
                    content="dados",
                    name="consultar_frota",
                    tool_call_id="call-1",
                ),
                AIMessage(content=""),
            ],
        }
        llm = Mock()
        llm.invoke.return_value = AIMessage(content="  ")

        with patch("src.utils.llm_adapter.get_llm", return_value=llm):
            with self.assertRaisesRegex(RuntimeError, "não produziu uma resposta textual"):
                format_frota(state)


if __name__ == "__main__":
    unittest.main()
