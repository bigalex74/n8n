import unittest

from ocr_review import compare_ocr_texts


class OcrReviewComparisonTests(unittest.TestCase):
    def test_close_candidate_removing_known_artifact_is_ready(self):
        result = compare_ocr_texts(
            '안녕하세요. 오늘도 좋은 하루입니다 f1...\n다음 줄도 그대로 유지합니다',
            '안녕하세요. 오늘도 좋은 하루입니다...\n다음 줄도 그대로 유지합니다',
        )
        self.assertEqual(result["verdict"], "candidate_ready")
        self.assertEqual(result["candidate"]["suspicious_latin"], [])

    def test_lost_lines_require_manual_review(self):
        result = compare_ocr_texts('첫째 줄\n둘째 줄\n셋째 줄', '첫째 줄')
        self.assertEqual(result["verdict"], "needs_review")
        self.assertGreater(result["lost_nonempty_lines"], 0)

    def test_punctuation_structure_change_requires_review(self):
        result = compare_ocr_texts('“안녕...”\n***', '안녕\n본문')
        self.assertEqual(result["verdict"], "needs_review")
        self.assertGreater(result["punctuation_delta"], 2)


if __name__ == "__main__":
    unittest.main()
