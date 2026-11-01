#!/usr/bin/env python3
"""Install Parler use; Codex-only extras require an explicit Codex target."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1]
IMAGE_REPO = "xixia0523/skills"
IMAGE_PATH = "Custom_Image_Generator_Skill/custom-imagegen"
IMAGE_REF = "a06ff55ab9fe712a069bf0760337de2b400895ed"


def install_skill(destination):
    if destination.resolve() == SOURCE:
        return
    if os.path.lexists(destination):
        source_files = {p.relative_to(SOURCE) for p in SOURCE.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        target_files = {p.relative_to(destination) for p in destination.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        if destination.is_dir() and not destination.is_symlink() and source_files == target_files and all(
                (destination / p).read_bytes() == (SOURCE / p).read_bytes() for p in source_files):
            print(f"parler-use 已安装且内容一致：{destination}")
            return
        raise RuntimeError(f"安装目标已存在，未覆盖：{destination}。请先检查已有内容，再自行决定如何处理。")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"已安装 parler-use：{destination}")


def install_image(skills_dir, codex_home):
    destination = skills_dir / "custom-imagegen"
    if os.path.lexists(destination):
        print(f"custom-imagegen 已存在，本次保留，不下载、不覆盖：{destination}")
        print("如需更新，请检查并自行移除旧安装后重新运行；外部配置应保留。")
        return
    helper = codex_home / "skills/.system/skill-installer/scripts/install-skill-from-github.py"
    if not helper.is_file():
        raise RuntimeError("未找到 Codex 内置 skill-installer。请在 Codex 中使用 $skill-installer 安装 "
                           f"https://github.com/{IMAGE_REPO}/tree/{IMAGE_REF}/{IMAGE_PATH} 后重试。")
    subprocess.run([sys.executable, str(helper), "--repo", IMAGE_REPO, "--ref", IMAGE_REF,
                    "--path", IMAGE_PATH, "--dest", str(skills_dir)], check=True)


def register_mcp(script):
    command = ["codex", "mcp", "add", "parler-usage", "--", sys.executable, str(script), "mcp"]
    if not shutil.which("codex"):
        print("未找到 Codex CLI；本地接口已随 skill 安装。请在 config.toml 中合并以下配置：")
        import json
        print('[mcp_servers.parler-usage]\ncommand = ' + json.dumps(sys.executable) +
              '\nargs = ' + json.dumps([str(script), "mcp"]))
        return
    existing = subprocess.run(["codex", "mcp", "get", "parler-usage"], capture_output=True)
    if existing.returncode == 0:
        print("parler-usage MCP 已存在，保留其配置。请用 codex mcp get parler-usage 检查路径。")
        return
    subprocess.run(command, check=True)
    print("已注册本地 parler-usage MCP（stdio，无监听端口）。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "other"), default="codex",
                        help="Codex installs custom-imagegen and its MCP; other installs only parler-use")
    parser.add_argument("--dest", type=Path, help="Codex skills 根目录；默认 $CODEX_HOME/skills")
    parser.add_argument("--skip-image", action="store_true", help="不安装生图 skill")
    parser.add_argument("--skip-mcp", action="store_true", help="不自动注册 Codex MCP")
    args = parser.parse_args()
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser().resolve()
    if args.client == "other" and not args.dest:
        parser.error("--client other requires --dest pointing to the target harness skills directory")
    skills_dir = (args.dest or codex_home / "skills").expanduser().resolve()
    try:
        destination = skills_dir / "parler-use"
        install_skill(destination)
        if args.client == "codex":
            if not args.skip_image:
                install_image(skills_dir, codex_home)
            if not args.skip_mcp:
                register_mcp(destination / "scripts/parler.py")
        else:
            print("已选择其他 AI 客户端：只安装 parler-use，不安装 custom-imagegen，也不注册 Codex MCP。")
        print("安装完成；下一轮对话可发现 skill。请在本机交互式终端录入个人凭据：")
        print(shlex.join([sys.executable, str(destination / "scripts/parler.py"), "configure"]))
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"安装未完成：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Install Parler use for a recipient; never overwrite an existing skill."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1]
IMAGE_REPO = "xixia0523/skills"
IMAGE_PATH = "Custom_Image_Generator_Skill/custom-imagegen"
IMAGE_REF = "a06ff55ab9fe712a069bf0760337de2b400895ed"


def install_skill(destination):
    if destination.resolve() == SOURCE:
        return
    if os.path.lexists(destination):
        source_files = {p.relative_to(SOURCE) for p in SOURCE.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        target_files = {p.relative_to(destination) for p in destination.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        if destination.is_dir() and not destination.is_symlink() and source_files == target_files and all(
                (destination / p).read_bytes() == (SOURCE / p).read_bytes() for p in source_files):
            print(f"parler-use 已安装且内容一致：{destination}")
            return
        raise RuntimeError(f"安装目标已存在，未覆盖：{destination}。请先检查已有内容，再自行决定如何处理。")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"已安装 parler-use：{destination}")


def install_image(skills_dir, codex_home):
    destination = skills_dir / "custom-imagegen"
    if os.path.lexists(destination):
        print(f"custom-imagegen 已存在，本次保留，不下载、不覆盖：{destination}")
        print("如需更新，请检查并自行移除旧安装后重新运行；外部配置应保留。")
        return
    helper = codex_home / "skills/.system/skill-installer/scripts/install-skill-from-github.py"
    if not helper.is_file():
        raise RuntimeError("未找到 Codex 内置 skill-installer。请在 Codex 中使用 $skill-installer 安装 "
                           f"https://github.com/{IMAGE_REPO}/tree/{IMAGE_REF}/{IMAGE_PATH} 后重试。")
    subprocess.run([sys.executable, str(helper), "--repo", IMAGE_REPO, "--ref", IMAGE_REF,
                    "--path", IMAGE_PATH, "--dest", str(skills_dir)], check=True)


def register_mcp(script):
    command = ["codex", "mcp", "add", "parler-usage", "--", sys.executable, str(script), "mcp"]
    if not shutil.which("codex"):
        print("未找到 Codex CLI；本地接口已随 skill 安装。请在 config.toml 中合并以下配置：")
        import json
        print('[mcp_servers.parler-usage]\ncommand = ' + json.dumps(sys.executable) +
              '\nargs = ' + json.dumps([str(script), "mcp"]))
        return
    existing = subprocess.run(["codex", "mcp", "get", "parler-usage"], capture_output=True)
    if existing.returncode == 0:
        print("parler-usage MCP 已存在，保留其配置。请用 codex mcp get parler-usage 检查路径。")
        return
    subprocess.run(command, check=True)
    print("已注册本地 parler-usage MCP（stdio，无监听端口）。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, help="Codex skills 根目录；默认 $CODEX_HOME/skills")
    parser.add_argument("--skip-image", action="store_true", help="不安装生图 skill")
    parser.add_argument("--skip-mcp", action="store_true", help="不自动注册 Codex MCP")
    args = parser.parse_args()
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser().resolve()
    skills_dir = (args.dest or codex_home / "skills").expanduser().resolve()
    try:
        destination = skills_dir / "parler-use"
        install_skill(destination)
        if not args.skip_image:
            install_image(skills_dir, codex_home)
        if not args.skip_mcp:
            register_mcp(destination / "scripts/parler.py")
        print("安装完成；下一轮对话可发现 skill。请在本机交互式终端录入个人凭据：")
        print(shlex.join([sys.executable, str(destination / "scripts/parler.py"), "configure"]))
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"安装未完成：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
