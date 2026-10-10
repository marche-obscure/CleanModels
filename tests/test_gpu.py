import unittest
from unittest import mock

from cleanmodels import gpu
from cleanmodels.gpu import Gpu, detect_gpus, exceeds_vram, gpus_from_registry_values, parse_nvidia_smi

GIB = 1024 ** 3
MIB = 1024 ** 2


class NvidiaSmiTest(unittest.TestCase):
    def test_single_card(self):
        self.assertEqual(parse_nvidia_smi("NVIDIA GeForce RTX 4090, 24564\n"),
                         [Gpu("NVIDIA GeForce RTX 4090", 24564 * MIB)])

    def test_several_cards_and_noise(self):
        output = "NVIDIA RTX A6000, 49140\r\n\r\nNVIDIA GeForce RTX 3060, 12288\r\nnot a line\n"
        self.assertEqual(parse_nvidia_smi(output), [
            Gpu("NVIDIA RTX A6000", 49140 * MIB),
            Gpu("NVIDIA GeForce RTX 3060", 12288 * MIB),
        ])

    def test_failure_returns_empty(self):
        with mock.patch("cleanmodels.gpu.subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(gpu.nvidia_gpus(), [])


class RegistryTest(unittest.TestCase):
    def test_qword_int_and_bytes(self):
        entries = [
            {"DriverDesc": "AMD Radeon RX 7900 XTX", "HardwareInformation.qwMemorySize": 24 * GIB},
            {"DriverDesc": "Intel Arc A770", "HardwareInformation.qwMemorySize": (16 * GIB).to_bytes(8, "little")},
        ]
        self.assertEqual(gpus_from_registry_values(entries), [
            Gpu("AMD Radeon RX 7900 XTX", 24 * GIB),
            Gpu("Intel Arc A770", 16 * GIB),
        ])

    def test_memory_size_fallback_and_zero_skipped(self):
        entries = [
            {"DriverDesc": "Old card", "HardwareInformation.MemorySize": (2 * GIB).to_bytes(4, "little")},
            {"DriverDesc": "Microsoft Basic Display Adapter"},
            {"DriverDesc": "Zero", "HardwareInformation.qwMemorySize": 0},
        ]
        self.assertEqual(gpus_from_registry_values(entries), [Gpu("Old card", 2 * GIB)])


class DetectTest(unittest.TestCase):
    def test_nvidia_plus_other_registry_cards_sorted_by_memory(self):
        nvidia = [Gpu("NVIDIA GeForce RTX 3060", 12 * GIB)]
        registry = [Gpu("NVIDIA GeForce RTX 3060", 12 * GIB), Gpu("AMD Radeon RX 7900 XTX", 24 * GIB)]
        with mock.patch("cleanmodels.gpu.nvidia_gpus", return_value=nvidia), \
                mock.patch("cleanmodels.gpu.registry_gpus", return_value=registry):
            self.assertEqual(detect_gpus(), [registry[1], nvidia[0]])

    def test_nothing_detected(self):
        with mock.patch("cleanmodels.gpu.nvidia_gpus", return_value=[]), \
                mock.patch("cleanmodels.gpu.registry_gpus", return_value=[]):
            self.assertEqual(detect_gpus(), [])


class ExceedsTest(unittest.TestCase):
    def test_threshold_includes_equality(self):
        self.assertTrue(exceeds_vram(8 * GIB, 8 * GIB))
        self.assertTrue(exceeds_vram(8 * GIB + 1, 8 * GIB))
        self.assertFalse(exceeds_vram(8 * GIB - 1, 8 * GIB))

    def test_unknown_vram_marks_nothing(self):
        self.assertFalse(exceeds_vram(100 * GIB, None))
        self.assertFalse(exceeds_vram(100 * GIB, 0))


if __name__ == "__main__":
    unittest.main()
