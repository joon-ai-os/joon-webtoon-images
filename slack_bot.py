import os
import re
import subprocess

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# 헤르메스 Slack 봇 (Socket Mode, 호스트에서 실행).
# - 허용 목록(파일)에 있는 사용자만 명령 실행
# - 메시지를 정해진 명령으로 해석해 docker exec 로 스크립트 실행 후 결과 회신
# - 아무나 "내아이디" 라고 보내면 자기 Slack ID를 알려줌(허용 목록에 추가할 때 사용)

APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
ALLOWED_FILE = os.environ.get("SLACK_ALLOWED_FILE", "/opt/hermes/slack_allowed.txt")

WORKSPACE = "/opt/data/workspace"
DEXEC = ["docker", "exec", "-u", "hermes", "-e", "HOME=/opt/data", "hermes", "python"]

app = App(token=BOT_TOKEN)

HELP = (
    "*헤르메스 명령*\n"
    "• `목록` — 카테고리(블로그) 목록\n"
    "• `동기화` — 계정에서 블로그 자동 갱신(새 블로그 추가)\n"
    "• `자동 <이름>` / `수동 <이름>` — 게시 모드 변경\n"
    "• `이름변경 <옛이름> <새이름>` — 카테고리 이름 변경\n"
    "• `웹툰 <화번호> <제목>` — 웹툰 스크롤형 초안 등록\n"
    "• `내아이디` — 내 Slack ID 확인\n"
    "• `도움말` — 이 안내"
)


def allowed_users():
    ids = set()
    try:
        with open(ALLOWED_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ids.add(line.split()[0])  # "U123  이름" 형식 허용
    except FileNotFoundError:
        pass
    return ids


def run(script, args):
    cmd = DEXEC + ["{}/{}".format(WORKSPACE, script)] + list(args)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return "⏱️ 시간 초과"
    res = (out.stdout or "") + (out.stderr or "")
    res = res.strip()
    if len(res) > 3500:
        res = res[:3500] + "\n…(생략)"
    return "```\n{}\n```".format(res) if res else "(출력 없음)"


def parse(text):
    """텍스트 -> ('help',) | ('whoami',) | ('cmd', script, [args]) | None"""
    t = text.strip()
    low = t.lower()

    if t in ("도움말", "help", "명령", "?"):
        return ("help",)
    if t in ("내아이디", "내 아이디", "whoami"):
        return ("whoami",)
    if t in ("목록", "카테고리", "리스트", "list", "블로그목록", "블로그 목록"):
        return ("cmd", "blog_cat.py", ["list"])
    if ("동기화" in t) or ("갱신" in t) or low == "sync":
        return ("cmd", "blog_sync.py", [])

    m = re.match(r"^자동\s+(.+)$", t) or re.match(r"^(.+?)\s+자동$", t)
    if m:
        return ("cmd", "blog_cat.py", ["mode", m.group(1).strip(), "auto"])
    m = re.match(r"^수동\s+(.+)$", t) or re.match(r"^(.+?)\s+수동$", t)
    if m:
        return ("cmd", "blog_cat.py", ["mode", m.group(1).strip(), "manual"])

    m = re.match(r"^이름변경\s+(\S+)\s+(.+)$", t)
    if m:
        return ("cmd", "blog_cat.py", ["rename", m.group(1), m.group(2).strip()])

    m = re.match(r"^웹툰\s+(\d+)\s*화?\s+(.+)$", t)
    if m:
        ep, title = m.group(1), m.group(2).strip()
        return ("cmd", "webtoon_post.py",
                ["--ep", ep, "--title", title, "--sub", "{}화".format(ep)])

    return None


try:
    BOT_USER_ID = app.client.auth_test().get("user_id")
except Exception:
    BOT_USER_ID = None


@app.event("message")
def on_message(event, say):
    if event.get("subtype") or event.get("bot_id"):
        return
    user = event.get("user")
    text = event.get("text", "") or ""
    if not user or not text.strip():
        return

    mentioned = bool(BOT_USER_ID) and ("<@{}>".format(BOT_USER_ID) in text)
    text = re.sub(r"<@[^>]+>", "", text).strip()

    parsed = parse(text)
    allowed = allowed_users()

    if parsed and parsed[0] == "whoami":
        say("너의 Slack ID: `{}` ({})".format(
            user, "허용됨 ✅" if user in allowed else "허용 안 됨 ❌"))
        return
    if parsed and parsed[0] == "help":
        say(HELP)
        return
    if parsed and parsed[0] == "cmd":
        if user not in allowed:
            say("권한이 없어요. 너의 ID: `{}` — 이 ID를 허용 목록에 추가하면 명령을 쓸 수 있어요.".format(user))
            return
        say(run(parsed[1], parsed[2]))
        return

    # 인식 못한 메시지: 봇을 @멘션했을 때만 안내(평소 잡담엔 조용)
    if mentioned:
        say("알 수 없는 명령이에요. `도움말` 을 보내보세요.")


if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
