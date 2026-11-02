# Qwen 3.8 27B Uncensored di Modal + OpenCode

Model: [junafinity/Qwen-3.8-27B-Uncensored](https://huggingface.co/junafinity/Qwen-3.8-27B-Uncensored) (BF16, ~52GB), vLLM, 1x H100 80GB.
VPS Ubuntu cuma buat deploy & tes; GPU-nya di Modal (ditagih per detik selama nyala).

Sudah diset di `app.py`: **min 0 GPU, max 1 GPU, mati setelah 2 menit idle**. Tidak perlu PATCH apa pun.
Fix dari percobaan Baseten sudah dibawa: anti-OOM (cudagraph 64, max-num-seqs 8, vision off) + quoting JSON benar.

## 0. Syarat
Akun di https://modal.com dengan kredit / payment method aktif (cek di dashboard > Usage & Billing).

## 1. Siapkan VPS
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git curl
python3 -m venv ~/modal-env && source ~/modal-env/bin/activate
pip install --upgrade modal
git clone https://github.com/nodepedia/qwen-modal.git ~/qwen-modal
```

## 2. Login Modal (token)
Generate di https://modal.com > Settings > API Tokens > New Token. Dapat `token-id` (ak-...) dan `token-secret` (as-...).
```bash
modal token set --token-id ak-XXXX --token-secret as-XXXX
modal profile current
```

## 3. Bikin API key buat endpoint kamu sendiri
Ini password endpoint-nya (bebas, bikin acak):
```bash
QWEN_API_KEY=$(openssl rand -hex 24)
sed -i '/QWEN_API_KEY/d' ~/.bashrc && echo "export QWEN_API_KEY=\"$QWEN_API_KEY\"" >> ~/.bashrc && source ~/.bashrc
modal secret create qwen-api-key QWEN_API_KEY="$QWEN_API_KEY" --force
```

## 4. Deploy (belum bayar GPU sampai ada request)
```bash
source ~/modal-env/bin/activate && cd ~/qwen-modal && git pull
modal deploy app.py
```
Output berisi URL, misal `https://NAMAKAMU--qwen38-serve.modal.run`. Simpan:
```bash
sed -i '/MODAL_URL/d' ~/.bashrc && echo 'export MODAL_URL="https://NAMAKAMU--qwen38-serve.modal.run"' >> ~/.bashrc && source ~/.bashrc
```

## 5. Tes (request pertama = cold start, MULAI BAYAR GPU)
Pertama kali lama (±10-20 menit: download 52GB ke volume + compile). Berikutnya lebih cepat karena bobot di-cache di volume `qwen38-cache`.
```bash
curl -s --max-time 1800 $MODAL_URL/v1/chat/completions \
  -H "Authorization: Bearer $QWEN_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen38-27b-uncensored","messages":[{"role":"user","content":"Halo"}],"max_tokens":200}'
```
Sukses kalau ada `"choices"`.

## 6. Cek status & log
```bash
modal app list                 # status app
modal container list           # GPU yang lagi nyala (kosong = tidak ditagih)
modal app logs qwen38          # log live (Ctrl+C keluar)
```

## 7. Stop / hapus
```bash
modal container stop CONTAINER_ID   # matikan GPU sekarang
modal app stop qwen38               # matikan app total
modal volume delete qwen38-cache    # hapus cache bobot (opsional)
```
Deploy ulang setelah ubah config: cukup `modal deploy app.py` lagi (versi lama otomatis diganti, tidak ada promote).

## 8. OpenCode
```bash
curl -fsSL https://opencode.ai/install | bash
mkdir -p ~/.config/opencode
sed "s|MODAL_URL|$MODAL_URL|" ~/qwen-modal/opencode.json > ~/.config/opencode/opencode.json
opencode
```

## Troubleshoot
| Gejala | Fix |
|---|---|
| 401 Unauthorized | `$QWEN_API_KEY` beda dengan secret; ulangi bagian 3 lalu `modal deploy app.py` |
| curl timeout / 303 di request pertama | cold start; tunggu, cek `modal app logs qwen38` |
| CUDA out of memory | ubah `--max-model-len 32768` jadi `16384` di `app.py`, deploy ulang |
| Error arsitektur `qwen3_5` | pin image vLLM ke versi yang support (mis. `vllm/vllm-openai:v0.33.0`) |
| Tagihan jalan terus | `modal container list`, lalu `modal container stop ID` |
