"""Valeurs fixées par la spécification."""

CONFIG_VERSION = 2

CATEGORIES = (
    "checkpoints",
    "controlnet",
    "diffusion_models",
    "LLM",
    "model_patches",
    "text_encoders",
    "unet",
    "vae",
)

MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".sft", ".onnx")

DEFAULT_JUNK_PATTERNS = ("*.part", "*.crdownload", "*.tmp", "*.download")
