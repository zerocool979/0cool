# download_datasets.py — Dataset Downloader for Nmap & SLM Integration

import os
import sys
import json
import random
import platform
import textwrap
import re
import time
from pathlib import Path

def _supports_color():
    if platform.system() == "Windows":
        return os.environ.get("WT_SESSION") or os.environ.get("ANSICON") or \
               os.environ.get("TERM_PROGRAM") == "vscode"
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOR = _supports_color()

def c(text, code):
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def cyan(t):   return c(t, "96")
def green(t):  return c(t, "92")
def yellow(t): return c(t, "93")
def red(t):    return c(t, "91")
def bold(t):   return c(t, "1")
def dim(t):    return c(t, "2")
def magenta(t):return c(t, "95")

def detect_environment():
    env = {
        "os"         : platform.system(),
        "os_release" : platform.release(),
        "python"     : platform.python_version(),
        "is_wsl"     : False,
        "is_colab"   : False,
        "is_jupyter" : False,
        "is_venv"    : False,
        "is_conda"   : False,
        "terminal"   : "unknown",
        "path_sep"   : os.sep,
    }

    try:
        with open("/proc/version", "r") as f:
            if "microsoft" in f.read().lower():
                env["is_wsl"] = True
    except FileNotFoundError:
        pass

    try:
        import google.colab
        env["is_colab"] = True
    except ImportError:
        pass

    try:
        shell = get_ipython().__class__.__name__ 
        if "ZMQ" in shell or "Jupyter" in shell or "Terminal" in shell:
            env["is_jupyter"] = True
    except NameError:
        pass

    if sys.prefix != sys.base_prefix:
        env["is_venv"] = True

    if os.environ.get("CONDA_DEFAULT_ENV"):
        env["is_conda"]   = True
        env["conda_env"]  = os.environ.get("CONDA_DEFAULT_ENV")

    term_prog = os.environ.get("TERM_PROGRAM", "")
    term      = os.environ.get("TERM", "")
    shell     = os.environ.get("SHELL", "")
    if "vscode" in term_prog.lower():
        env["terminal"] = "VS Code Integrated Terminal"
    elif os.environ.get("WT_SESSION"):
        env["terminal"] = "Windows Terminal"
    elif "xterm" in term or "screen" in term:
        env["terminal"] = f"xterm-compatible ({term})"
    elif "bash" in shell:
        env["terminal"] = "Bash"
    elif "zsh" in shell:
        env["terminal"] = "Zsh"
    elif "fish" in shell:
        env["terminal"] = "Fish"
    elif platform.system() == "Windows":
        env["terminal"] = "CMD / PowerShell"

    return env

def print_env_info(env):
    print(bold(cyan("\n┌─ Environment Terdeteksi ──────────────────────────────")))
    flags = []
    if env["is_wsl"]:     flags.append(yellow("WSL"))
    if env["is_colab"]:   flags.append(yellow("Google Colab"))
    if env["is_jupyter"]: flags.append(yellow("Jupyter"))
    if env["is_venv"]:    flags.append(green("virtualenv aktif"))
    if env["is_conda"]:   flags.append(green(f"conda: {env.get('conda_env','')}"))

    os_label = env["os"]
    if env["is_wsl"]: os_label += " (via WSL)"

    print(f"│  OS       : {cyan(os_label)} {env['os_release']}")
    print(f"│  Python   : {cyan(env['python'])}")
    print(f"│  Terminal : {cyan(env['terminal'])}")
    print(f"│  Extras   : {' '.join(flags) if flags else dim('none')}")
    print(bold(cyan("└───────────────────────────────────────────────────────\n")))

def ensure_library(module_name, pip_name=None, env=None):

    pip_name = pip_name or module_name
    try:
        return __import__(module_name)
    except ImportError:
        print(yellow(f"  ⚙  '{pip_name}' belum terinstall. Menginstall..."))

        if env and env.get("is_colab"):
            cmd = f"{sys.executable} -m pip install {pip_name} -q"
        elif env and env.get("is_conda"):
            cmd = f"{sys.executable} -m pip install {pip_name} -q"
        else:
            cmd = f"{sys.executable} -m pip install {pip_name} -q"

        ret = os.system(cmd)
        if ret != 0:
            print(red(f"  ✗  Gagal install '{pip_name}'. Install manual:"))
            print(red(f"     pip install {pip_name}"))
            sys.exit(1)

        print(green(f"  ✓  '{pip_name}' berhasil diinstall.\n"))
        return __import__(module_name)

def print_banner():
    banner = r"""
  ███╗   ██╗███╗   ███╗ █████╗ ██████╗     ███████╗██╗     ███╗   ███╗
  ████╗  ██║████╗ ████║██╔══██╗██╔══██╗    ██╔════╝██║     ████╗ ████║
  ██╔██╗ ██║██╔████╔██║███████║██████╔╝    ███████╗██║     ██╔████╔██║
  ██║╚██╗██║██║╚██╔╝██║██╔══██║██╔═══╝     ╚════██║██║     ██║╚██╔╝██║
  ██║ ╚████║██║ ╚═╝ ██║██║  ██║██║         ███████║███████╗██║ ╚═╝ ██║
  ╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝         ╚══════╝╚══════╝╚═╝     ╚═╝
    """
    print(cyan(banner))
    print(bold("  Dataset Downloader & Processor — Nmap Fine-tuning Pipeline"))
    print(dim("  Qwen 1.8B · HuggingFace · JSONL · Nmap-filtered\n"))
    print("  " + "─" * 55)

def prompt(text, valid=None, default=None):
    while True:
        hint = ""
        if valid:
            hint = " [" + "/".join(valid) + "]"
        if default:
            hint += f" (default: {default})"
        try:
            val = input(f"\n  {bold(cyan('?'))} {text}{hint}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(red("\n\n  Dibatalkan oleh user. Keluar."))
            sys.exit(0)
        if not val and default:
            return default
        if valid and val not in valid:
            print(yellow(f"    Pilihan tidak valid. Masukkan salah satu dari: {', '.join(valid)}"))
            continue
        if val:
            return val

def prompt_multiline(label):
    print(f"\n  {bold(cyan('?'))} {label}")
    print(dim("    (Masukkan satu per baris. Tekan Enter kosong jika sudah selesai)"))
    items = []
    idx = 1
    while True:
        try:
            val = input(f"    [{idx}] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not val:
            if not items:
                print(yellow("    Minimal masukkan 1 item."))
                continue
            break
        items.append(val)
        idx += 1
    return items

def progress_bar(current, total, prefix="", width=35):
    filled = int(width * current / max(total, 1))
    bar    = "█" * filled + "░" * (width - filled)
    pct    = int(100 * current / max(total, 1))
    print(f"\r    {prefix} [{cyan(bar)}] {pct:3d}% ({current}/{total})", end="", flush=True)

# ─────────────────────────────────────────────
# IDENTIFIKASI FORMAT FILE
# ─────────────────────────────────────────────

def detect_file_format(path):
    ext = Path(path).suffix.lower()
    mapping = {
        ".jsonl"  : "jsonl",
        ".json"   : "json",
        ".parquet": "parquet",
        ".txt"    : "txt",
        ".csv"    : "csv",
    }
    return mapping.get(ext, "unknown")

def parse_hf_url(url):
    url = url.strip().rstrip("/")
    match = re.search(r"huggingface\.co/datasets/([^/\s]+/[^/\s]+)", url)
    if match:
        return match.group(1)
    if "/" in url and "huggingface" not in url and "http" not in url:
        return url
    return None

def filter_nmap(example):
    text = str(example).lower()
    return bool(re.search(r'(?<![a-z])nmap(?![a-z])', text))


def normalize(example, source):
    """
    Normalisasi satu contoh data dari berbagai format ke format standar:
    { instruction, input, output, source }
    """
    try:
        if isinstance(example, dict) and "messages" in example:
            messages = example.get("messages", [])
            user_msg = next((m.get("content","") for m in messages if m.get("role") == "user"), "")
            asst_msg = next((m.get("content","") for m in messages if m.get("role") == "assistant"), "")
            if user_msg and asst_msg:
                return {"instruction": user_msg, "input": "", "output": asst_msg, "source": source}

        if isinstance(example, dict) and "goal" in example and "reconnaissance" in example:
            goal      = example.get("goal", "")
            recon     = example.get("reconnaissance", [])
            thinking  = example.get("thinking", [])
            recon_cmds = [
                r.get("command", "") for r in recon
                if isinstance(r, dict) and r.get("tool") == "nmap"
            ]
            if recon_cmds:
                thinking_text = "\n".join(thinking) if isinstance(thinking, list) else str(thinking)
                return {
                    "instruction": f"Lakukan reconnaissance untuk: {goal}",
                    "input"      : "",
                    "output"     : f"Thinking:\n{thinking_text}\n\nNmap Commands:\n" + "\n".join(recon_cmds),
                    "source"     : source,
                }

        if isinstance(example, dict) and "scan_results" in example and "report" in example:
            return {
                "instruction": "Buat laporan pentest dari hasil scan berikut",
                "input"      : str(example.get("scan_results", "")),
                "output"     : str(example.get("report", "")),
                "source"     : source,
            }

        if isinstance(example, dict) and "INSTRUCTION" in example:
            return {
                "instruction": str(example.get("INSTRUCTION", "")),
                "input"      : str(example.get("INPUT", "")),
                "output"     : str(example.get("RESPONSE", example.get("OUTPUT", ""))),
                "source"     : source,
            }

        if isinstance(example, dict):
            instr  = str(example.get("instruction", example.get("prompt", example.get("query", ""))))
            inp    = str(example.get("input", ""))
            output = str(example.get("output",
                         example.get("response",
                         example.get("answer",
                         example.get("completion", "")))))
            if instr and output:
                return {"instruction": instr, "input": inp, "output": output, "source": source}

        if isinstance(example, str) and len(example) > 30:
            return {"instruction": "Analisis teks berikut:", "input": "", "output": example, "source": source}

    except Exception:
        pass
    return None


def process_examples(examples, source_name, show_progress=True):
    results = []
    total   = len(examples) if hasattr(examples, "__len__") else 0
    count   = 0

    for example in examples:
        count += 1
        if show_progress and total and count % 200 == 0:
            progress_bar(count, total, prefix=f"{source_name:30s}")

        if not filter_nmap(example):
            continue
        norm = normalize(example, source_name)
        if norm and norm.get("instruction") and norm.get("output"):
            results.append(norm)

    if show_progress and total:
        progress_bar(total, total, prefix=f"{source_name:30s}")
        print()

    return results

def load_file(path, env):
    fmt  = detect_file_format(path)
    path = Path(path)

    if not path.exists():
        print(red(f"    ✗ File tidak ditemukan: {path}"))
        return []

    print(f"    Membaca {cyan(str(path))} [{yellow(fmt)}] ...", end=" ")

    try:
        if fmt == "jsonl":
            data = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            print(green(f"✓ {len(data)} rows"))
            return data

        if fmt == "json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                print(green(f"✓ {len(data)} rows"))
                return data
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        print(green(f"✓ {len(v)} rows"))
                        return v
            print(green("✓ 1 row"))
            return [data]

        if fmt == "parquet":
            pd = ensure_library("pandas", "pandas", env)
            df = pd.read_parquet(path)
            data = df.to_dict(orient="records")
            print(green(f"✓ {len(data)} rows"))
            return data

        if fmt == "csv":
            import csv
            data = []
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(dict(row))
            print(green(f"✓ {len(data)} rows"))
            return data

        if fmt == "txt":
            with open(path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            data = []
            for line in lines:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    data.append(line)
            print(green(f"✓ {len(data)} rows"))
            return data

    except Exception as e:
        print(red(f"\n    ✗ Error membaca file: {e}"))
        return []

    print(red(f"\n    ✗ Format '{fmt}' tidak didukung."))
    return []


def load_hf_dataset(dataset_id, env):
    ensure_library("datasets", "datasets", env)
    from datasets import load_dataset  # noqa

    print(f"    Mengunduh {cyan(dataset_id)} dari HuggingFace ...", end=" ", flush=True)
    try:
        ds = load_dataset(dataset_id, split="train")
        print(green(f"✓ {len(ds)} rows"))
        return list(ds)
    except Exception as e:
        try:
            ds = load_dataset(dataset_id)
            first_split = list(ds.keys())[0]
            print(green(f"✓ {len(ds[first_split])} rows [{first_split}]"))
            return list(ds[first_split])
        except Exception as e2:
            print(red(f"\n    ✗ Gagal download: {e2}"))
            return []

def scenario_download(env):
    print(bold(cyan(" Download dari HuggingFace - Masukkan URL dataset HuggingFace (satu per baris)")))

    print(dim("\n  Contoh URL yang valid:"))
    print(dim("    https://huggingface.co/datasets/0dAI/PentestingCommandLogic"))
    print(dim("    0dAI/PentestingCommandLogic  ← format pendek juga diterima\n"))

    urls = prompt_multiline("Masukkan URL / Dataset ID HuggingFace:")

    all_data = []
    for url in urls:
        dataset_id = parse_hf_url(url)
        if not dataset_id:
            print(yellow(f"  ⚠  Tidak dapat mem-parse URL: {url}  → dilewati"))
            continue

        source_name = dataset_id.split("/")[-1]

        print(f"\n  {bold('▶')} Memproses: {cyan(dataset_id)}")
        raw = load_hf_dataset(dataset_id, env)

        if not raw:
            print(yellow(f"    ⚠  Dataset kosong atau gagal diunduh. Dilewati."))
            continue

        filtered = process_examples(raw, source_name)
        print(f"    {green('✓')} Nmap-filtered: {bold(str(len(filtered)))} baris ditemukan")
        all_data.extend(filtered)

    return all_data

def scenario_local(env):
    print(bold(cyan("\n  Proses dari File Lokal - Masukkan path file dataset (relatif atau absolut)")))

    print(dim("\n  Contoh path yang valid:"))
    print(dim("    pentest-agent-dataset-chatml/dataset.jsonl"))
    print(dim("    datasets/PentestingCommandLogic/dataset_comandos.jsonl"))
    print(dim("    /home/user/data/pentesting-for-agents/data/train-00000-of-00001.parquet"))

    if env["os"] == "Windows" or env["is_wsl"]:
        print(dim("    C:\\Users\\user\\datasets\\mydata.jsonl  ← path Windows juga OK"))
    print()

    paths = prompt_multiline("Masukkan path file dataset:")

    all_data = []
    for raw_path in paths:
        norm_path = raw_path.replace("\\", os.sep).replace("/", os.sep)
        p = Path(norm_path)

        if not p.is_absolute():
            script_dir = Path(__file__).parent
            p = script_dir / p

        source_name = p.stem

        print(f"\n  {bold('▶')} Memproses: {cyan(str(p))}")
        raw = load_file(str(p), env)

        if not raw:
            print(yellow(f"    ⚠  File kosong atau gagal dibaca. Dilewati."))
            continue

        filtered = process_examples(raw, source_name)
        print(f"    {green('✓')} Nmap-filtered: {bold(str(len(filtered)))} baris ditemukan")
        all_data.extend(filtered)

    return all_data

def save_dataset(all_data, output_dir=None, env=None):
    if not all_data:
        print(red("\n  ✗ Tidak ada data yang berhasil diproses. File output tidak dibuat."))
        return

    random.shuffle(all_data)

    split_idx  = int(len(all_data) * 0.85)
    train_data = all_data[:split_idx]
    test_data  = all_data[split_idx:]

    if output_dir is None:
        output_dir = Path(__file__).parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "nmap_train.jsonl"
    test_path  = output_dir / "nmap_test.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(test_path, "w", encoding="utf-8") as f:
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(bold(cyan("\n  ┌─ Hasil ───────────────────────────────────────────────")))
    print(f"  │  Total data     : {bold(str(len(all_data)))} rows")
    print(f"  │  Train (85%)    : {bold(str(len(train_data)))} rows → {green(str(train_path))}")
    print(f"  │  Test  (15%)    : {bold(str(len(test_data)))} rows  → {green(str(test_path))}")

    from collections import Counter
    sources = Counter(d.get("source", "?") for d in all_data)
    print(f"  │")
    print(f"  │  Distribusi source:")
    for src, cnt in sources.most_common():
        bar = "▓" * int(20 * cnt / len(all_data))
        print(f"  │    {src:35s} {yellow(str(cnt)):>6} {dim(bar)}")

    print(bold(cyan("  └───────────────────────────────────────────────────────")))
    print(f"\n  {green('✓')} Dataset siap!\n")

def main():
    print_banner()
    env = detect_environment()
    print_env_info(env)

    print("  Sebelum mulai, satu pertanyaan:\n")
    print(f"  {bold('1')}  {green('Belum')} — Dataset belum didownload, minta script unduhkan sekarang")
    print(f"  {bold('2')}  {yellow('Sudah')} — Dataset sudah ada di lokal, langsung proses\n")

    choice = prompt("Apakah dataset sudah didownload?", valid=["1", "2"])

    if choice == "1":
        all_data = scenario_download(env)
    else:
        all_data = scenario_local(env)

    if all_data:
        print(f"\n  {bold(green('✓'))} Total data terkumpul: {bold(cyan(str(len(all_data))))} rows")

        use_custom = prompt("Simpan output ke direktori ini (lokasi script)?", valid=["y", "n"], default="y")
        output_dir = None
        if use_custom == "n":
            custom_path = prompt("Masukkan path direktori output")
            output_dir = custom_path

        save_dataset(all_data, output_dir=output_dir, env=env)
    else:
        print(red("\n  Tidak ada data yang berhasil dikumpulkan."))
        print(yellow("  Periksa kembali URL atau path yang kamu masukkan.\n"))
        sys.exit(1)


if __name__ == "__main__":
    main()
