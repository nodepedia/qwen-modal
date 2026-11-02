import subprocess
import modal

MODEL = "junafinity/Qwen-3.8-27B-Uncensored"
SERVED = "qwen38-27b-uncensored"

image = (
    modal.Image.from_registry("vllm/vllm-openai:latest", add_python=None)
    .entrypoint([])
    .env({
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        "HF_XET_HIGH_PERFORMANCE": "1",
        "HF_HOME": "/cache/hf",
    })
)

cache = modal.Volume.from_name("qwen38-cache", create_if_missing=True)
app = modal.App("qwen38")


@app.function(
    image=image,
    gpu="H100",
    min_containers=0,        # mati total saat idle
    max_containers=1,        # maksimal 1 GPU
    scaledown_window=120,    # mati setelah 2 menit idle
    timeout=60 * 60,
    volumes={"/cache": cache},
    secrets=[modal.Secret.from_name("qwen-api-key")],
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=8000, startup_timeout=30 * 60)
def serve():
    cmd = (
        f"vllm serve {MODEL} --served-model-name {SERVED} "
        "--host 0.0.0.0 --port 8000 "
        "--max-model-len 32768 --gpu-memory-utilization 0.90 "
        "--max-num-seqs 8 --max-cudagraph-capture-size 64 "
        "--limit-mm-per-prompt '{\"image\":0,\"video\":0}' "
        "--enable-auto-tool-choice --tool-call-parser qwen3_coder "
        "--reasoning-parser qwen3 "
        "--download-dir /cache/hf "
        "--api-key \"$QWEN_API_KEY\""
    )
    subprocess.Popen(cmd, shell=True)
