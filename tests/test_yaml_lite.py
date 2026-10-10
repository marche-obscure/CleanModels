import unittest

from cleanmodels.yaml_lite import YamlError, parse


class YamlLiteTest(unittest.TestCase):
    def test_nested_mapping_and_comments(self):
        text = "# entête\ncomfyui:\n  base_path: D:/AI/  # fin\n  checkpoints: models/checkpoints\n"
        self.assertEqual(parse(text), {"comfyui": {"base_path": "D:/AI/", "checkpoints": "models/checkpoints"}})

    def test_block_literal(self):
        text = "a:\n  unet: |\n    models/unet\n    other/unet\n  vae: v\n"
        self.assertEqual(parse(text), {"a": {"unet": "models/unet\nother/unet", "vae": "v"}})

    def test_quotes(self):
        self.assertEqual(parse('k: "a # b"\n'), {"k": "a # b"})
        self.assertEqual(parse("k: 'x'\n"), {"k": "x"})

    def test_crlf_and_backslashes(self):
        text = "s:\r\n  base_path: D:\\AI\\\r\n  vae: models\\vae\r\n"
        self.assertEqual(parse(text), {"s": {"base_path": "D:\\AI\\", "vae": "models\\vae"}})

    def test_empty_value_is_empty_dict_or_string(self):
        self.assertEqual(parse("s:\n"), {"s": {}})

    def test_bad_indent_raises(self):
        with self.assertRaises(YamlError) as ctx:
            parse("s:\n  a: 1\n b: 2\n")
        self.assertEqual(ctx.exception.line, 3)

    def test_tab_indent_raises(self):
        with self.assertRaises(YamlError):
            parse("s:\n\ta: 1\n")


if __name__ == "__main__":
    unittest.main()
