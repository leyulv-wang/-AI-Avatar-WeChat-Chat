from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
import shutil
import socket


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--backend-host", default="127.0.0.1")
    parser.add_argument("--backend-reload", action="store_true")
    parser.add_argument("--frontend-port", type=int, default=5173)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    web_dir = root / "web"

    if not web_dir.exists():
        print("web 目录不存在", file=sys.stderr)
        return 1

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "wxbot.main:app",
        "--host",
        args.backend_host,
        "--port",
        str(args.backend_port),
    ]
    if args.backend_reload:
        backend_cmd.extend(
            [
                "--reload",
                "--reload-dir",
                "wxbot",
                "--reload-dir",
                "scripts",
                "--reload-exclude",
                "data",
                "--reload-exclude",
                "backups",
                "--reload-exclude",
                "secrets",
            ]
        )

    frontend_exe = _find_frontend_runner()
    if not frontend_exe:
        print("未找到前端包管理器：请安装 pnpm（推荐）或 npm，并确保在 PATH 中可用", file=sys.stderr)
        print("- pnpm: https://pnpm.io/installation", file=sys.stderr)
        print("- npm: 安装 Node.js 后自带 npm", file=sys.stderr)
        return 1

    frontend_host = "0.0.0.0"
    if _is_pnpm(frontend_exe):
        frontend_cmd = [frontend_exe, "exec", "vite", "--host", frontend_host, "--port", str(args.frontend_port)]
    elif _is_yarn(frontend_exe):
        frontend_cmd = [frontend_exe, "vite", "--host", frontend_host, "--port", str(args.frontend_port)]
    else:
        frontend_cmd = [frontend_exe, "exec", "vite", "--", "--host", frontend_host, "--port", str(args.frontend_port)]

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    if not _is_port_free(args.backend_host, args.backend_port):
        print(
            f"后端端口被占用：{args.backend_host}:{args.backend_port}。\n"
            "请先停止占用该端口的旧后端进程，再重试一键启动。",
            file=sys.stderr,
        )
        return 1

    backend = _popen(backend_cmd, cwd=str(root), env=env)
    try:
        time.sleep(0.3)
        frontend = _popen(frontend_cmd, cwd=str(web_dir), env=env)
    except Exception as e:
        _terminate_tree(backend)
        print(f"前端启动失败：{e}", file=sys.stderr)
        return 1

    try:
        while True:
            b = backend.poll()
            f = frontend.poll()
            if b is not None or f is not None:
                _terminate_tree(frontend)
                _terminate_tree(backend)
                return b if b is not None else (f or 0)
            time.sleep(0.5)
    except KeyboardInterrupt:
        _terminate_tree(frontend)
        _terminate_tree(backend)
        return 0


def _popen(cmd: list[str], *, cwd: str, env: dict[str, str]) -> subprocess.Popen:
    if os.name == "nt":
        exe0 = cmd[0]
        if exe0.lower().endswith((".cmd", ".bat")):
            cmd = ["cmd.exe", "/c", exe0, *cmd[1:]]
        return subprocess.Popen(cmd, cwd=cwd, env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    return subprocess.Popen(cmd, cwd=cwd, env=env, start_new_session=True)


def _find_frontend_runner() -> str | None:
    for exe in ["pnpm", "pnpm.cmd", "npm", "npm.cmd", "yarn", "yarn.cmd"]:
        p = shutil.which(exe)
        if p:
            return p
    return None


def _is_pnpm(exe: str) -> bool:
    return Path(exe).name.lower().startswith("pnpm")


def _is_yarn(exe: str) -> bool:
    return Path(exe).name.lower().startswith("yarn")


def _terminate_tree(p: subprocess.Popen | None) -> None:
    if p is None:
        return
    if p.poll() is not None:
        return

    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(p.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            return
        return

    try:
        p.terminate()
    except Exception:
        return
    for _ in range(20):
        if p.poll() is not None:
            return
        time.sleep(0.2)
    try:
        p.kill()
    except Exception:
        return


def _is_port_free(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
        return True
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
