from __future__ import annotations

from io import BytesIO
from pathlib import Path
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from app.agents.qa_agent import answer_user_question
from app.agents.sft_dataset_agent import build_sft_dataset
from app.agents.table_query_agent import run_table_query
from app.agents.workflow_agent import WorkflowConfig, run_analysis_workflow
from app.data.loader import list_excel_sheets, load_dataset


ROOT_DIR = Path(__file__).resolve().parents[1]


class DeploymentSmokeTest(unittest.TestCase):
    def _run_sample(self, filename: str):
        sample_path = ROOT_DIR / "sample_data" / filename
        with sample_path.open("rb") as file:
            dataframe = load_dataset(file, filename)
        result = run_analysis_workflow(
            dataframe,
            WorkflowConfig(dataset_name=filename, language="zh"),
        )
        return dataframe, result

    def test_sample_data_end_to_end(self) -> None:
        for filename in ["customer_churn_sample.csv", "customer_churn_quality_demo.csv"]:
            with self.subTest(filename=filename):
                dataframe, result = self._run_sample(filename)
                self.assertGreater(len(dataframe), 0)
                self.assertEqual(len(result.steps), 6)
                self.assertFalse(result.profile_df.empty)
                self.assertIn("DataInsight Agent", result.markdown_report)
                self.assertIn("<!doctype html>", result.html_report)

                query = run_table_query(dataframe, "SELECT * FROM dataset LIMIT 5")
                self.assertIsNone(query.error)
                self.assertEqual(len(query.result_df), min(5, len(dataframe)))

                blocked_query = run_table_query(dataframe, "DROP TABLE dataset")
                self.assertIsNotNone(blocked_query.error)

                qa = answer_user_question(
                    "主要数据质量风险是什么？",
                    result,
                    ROOT_DIR / "knowledge_base",
                    "zh",
                )
                self.assertEqual(qa.mode, "local")
                self.assertTrue(qa.answer)

                sft = build_sft_dataset(result, "zh")
                self.assertEqual(len(sft.samples), 5)
                self.assertEqual(len(sft.jsonl.splitlines()), 5)

    def test_xlsx_upload_and_sheet_selection(self) -> None:
        workbook = BytesIO()
        expected = pd.DataFrame({"customer_id": [1, 2], "churn": [0, 1]})
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            expected.to_excel(writer, sheet_name="Customers", index=False)
        workbook.name = "customers.xlsx"

        self.assertEqual(list_excel_sheets(workbook), ["Customers"])
        actual = load_dataset(workbook, workbook.name, sheet_name="Customers")
        pd.testing.assert_frame_equal(actual, expected)
        first_sheet = load_dataset(workbook, workbook.name)
        pd.testing.assert_frame_equal(first_sheet, expected)

    def test_empty_excel_sheet_is_rejected_before_analysis(self) -> None:
        workbook = BytesIO()
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            pd.DataFrame().to_excel(writer, sheet_name="Empty", index=False)
        workbook.name = "empty.xlsx"

        with self.assertRaisesRegex(ValueError, "does not contain any columns"):
            load_dataset(workbook, workbook.name, sheet_name="Empty")

    def test_streamlit_initial_render_and_sample_flow(self) -> None:
        app = AppTest.from_file(
            str(ROOT_DIR / "frontend" / "streamlit_app.py"),
            default_timeout=60,
        ).run()
        self.assertEqual(len(app.exception), 0)

        sample_selectbox = next(
            selectbox
            for selectbox in app.selectbox
            if "Customer churn quality demo" in selectbox.options
        )
        sample_selectbox.select("Customer churn quality demo").run()
        self.assertEqual(len(app.exception), 0)
        self.assertGreaterEqual(len(app.metric), 10)
        self.assertGreaterEqual(len(app.dataframe), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
