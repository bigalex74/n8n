import unittest

from app.text_layout import DotRun, OcrLine, order_lines, render_text, restore_dot_runs


class TextLayoutTests(unittest.TestCase):
    def test_orders_numerically_by_rows(self):
        lines = [
            OcrLine("second", 0.9, [10, 40, 100, 60]),
            OcrLine("first", 0.9, [10, 10, 100, 30]),
        ]
        self.assertEqual([line.text for line in order_lines(lines)], ["first", "second"])

    def test_inserts_blank_line_for_large_vertical_gap(self):
        lines = [
            OcrLine("문장 하나", 0.9, [10, 10, 100, 30]),
            OcrLine("문장 둘", 0.9, [10, 60, 100, 80]),
        ]
        self.assertEqual(render_text(lines), "문장 하나\n\n문장 둘\n")

    def test_merges_fragments_on_the_same_visual_row(self):
        lines = [
            OcrLine("문장", 0.9, [10, 10, 70, 30]),
            OcrLine("하나.", 0.8, [80, 11, 140, 31]),
        ]
        self.assertEqual(render_text(lines), "문장 하나.\n")

    def test_keeps_word_space_between_detected_fragments(self):
        lines = [
            OcrLine("복잡하", 0.9, [10, 10, 100, 30]),
            OcrLine("게", 0.9, [102, 10, 120, 30]),
        ]
        self.assertEqual(render_text(lines), "복잡하 게\n")

    def test_deduplicates_overlapping_syllable_without_double_space(self):
        lines = [
            OcrLine("같은 인간을", 0.9, [10, 10, 100, 30]),
            OcrLine("을 혐오한다", 0.9, [95, 10, 170, 30]),
        ]
        self.assertEqual(render_text(lines), "같은 인간을 혐오한다\n")

    def test_adds_space_after_sentence_punctuation(self):
        self.assertEqual(
            render_text([OcrLine("다.그의 말,이것", 0.9)]),
            "다. 그의 말, 이것\n",
        )

    def test_normalizes_star_variants(self):
        self.assertEqual(render_text([OcrLine("∗∗*", 0.9)]), "***\n")

    def test_restores_ellipsis_inside_recognized_line(self):
        lines = [OcrLine('“응그것도 고마워.”', 0.9, [100, 100, 600, 180])]
        runs = [DotRun(175, 160, 210, 168, 3)]
        self.assertEqual(
            render_text(restore_dot_runs(lines, runs)),
            '“응... 그것도 고마워.”\n',
        )

    def test_restores_punctuation_only_line_between_quotes(self):
        lines = [
            OcrLine('"', 0.9, [100, 100, 120, 130]),
            OcrLine('"', 0.9, [220, 100, 240, 130]),
        ]
        runs = [DotRun(130, 125, 210, 133, 7)]
        self.assertEqual(render_text(restore_dot_runs(lines, runs)), '"......."\n')

    def test_skips_empty_lines(self):
        self.assertEqual(render_text([OcrLine(" ", 0.9)]), "")


if __name__ == "__main__":
    unittest.main()
