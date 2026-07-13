import json
import os

import webtoon_post as wp

# 매일 실행: 각 시리즈의 '다음 화'를 초안으로 등록한다.
# - 다음 화 > 총화수  → 완결, 게시 없음
# - 이미지 아직 없음   → 건너뜀(다음날 재시도)
# - 마지막 화          → "완결" 문구
# 설정+진행상태는 webtoon_series.json 한 파일에 둔다.

SERIES_FILE = os.environ.get("WEBTOON_SERIES", "/opt/data/workspace/webtoon_series.json")
TITLES_FILE = os.environ.get("WEBTOON_TITLES", "/opt/data/workspace/webtoon_titles.json")


def load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def run_series(slug, cfg, titles):
    total = int(cfg.get("total", 20))
    posted = int(cfg.get("posted", 0))
    gh = cfg.get("gh", wp.GH_DEFAULT)
    blog = cfg.get("blog_id", wp.BLOG_DEFAULT)
    nxt = posted + 1

    if nxt > total:
        print("[{}] 완결 상태 (총 {}화 게시 완료) → 게시 없음".format(slug, total))
        return False

    path = "{}/ep{:02d}/".format(slug, nxt)
    cuts = wp.count_cuts(gh, path, nxt)
    if cuts <= 0:
        print("[{}] {}화 이미지 아직 없음 → 건너뜀".format(slug, nxt))
        return False

    title = titles.get(str(nxt), "")
    is_last = (nxt == total)
    blog_title, url = wp.post(nxt, title, "{}화".format(nxt), cuts, gh, path, blog, False, is_last)
    cfg["posted"] = nxt
    print("[{}] {}화 초안 등록 ({}컷){}".format(slug, nxt, cuts, " · 완결" if is_last else ""))
    print("  제목:", blog_title)
    print("  URL:", url)
    return True


def main():
    series = load(SERIES_FILE, None)
    if not series:
        print("설정 파일 없음:", SERIES_FILE, "→ 아무것도 안 함")
        return
    titles = load(TITLES_FILE, {})
    for slug, cfg in series.items():
        try:
            run_series(slug, cfg, titles)
        except Exception as e:
            print("[{}] 오류: {}".format(slug, e))
    save(SERIES_FILE, series)


if __name__ == "__main__":
    main()
