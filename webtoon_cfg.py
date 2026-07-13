import json
import os
import sys

# 웹툰 시리즈 설정/진행상태 관리 (Slack '웹툰상태' / '웹툰총화수 N' 에서 호출).
#   python webtoon_cfg.py status
#   python webtoon_cfg.py total 20     # 총 화수 변경
#   python webtoon_cfg.py posted 1     # 게시 포인터 수동 조정(다음 실행은 posted+1)

SERIES_FILE = os.environ.get("WEBTOON_SERIES", "/opt/data/workspace/webtoon_series.json")
SLUG = os.environ.get("WEBTOON_SLUG", "3minutes-luxury")
NAME = "3분의 사치"


def load():
    try:
        with open(SERIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save(d):
    with open(SERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def main():
    args = sys.argv[1:]
    d = load()
    cfg = d.get(SLUG, {"total": 20, "posted": 0})

    if not args or args[0] == "status":
        total = int(cfg.get("total", 20))
        posted = int(cfg.get("posted", 0))
        if posted >= total:
            state = "완결 ✅"
        else:
            state = "다음 게시: {}화".format(posted + 1)
        print("{} — 총 {}화 / 게시 {}화까지 / {}".format(NAME, total, posted, state))
        return

    if args[0] == "total" and len(args) >= 2:
        cfg["total"] = int(args[1])
        d[SLUG] = cfg
        save(d)
        print("총 화수 변경: {}화".format(cfg["total"]))
        return

    if args[0] == "posted" and len(args) >= 2:
        cfg["posted"] = int(args[1])
        d[SLUG] = cfg
        save(d)
        print("게시 포인터 변경: {}화 (다음 실행은 {}화)".format(cfg["posted"], cfg["posted"] + 1))
        return

    print("사용법: webtoon_cfg.py [status | total N | posted N]")


if __name__ == "__main__":
    main()
