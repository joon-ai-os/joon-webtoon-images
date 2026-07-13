import os
import re
import argparse
import requests

# 웹툰을 '큰 화면 세로 스크롤'로 Blogger에 투고한다.
# 컷 수(--cuts)를 주지 않으면 GitHub 폴더에서 자동으로 센다.
# 다른 스크립트(webtoon_daily.py)에서 post()/count_cuts()를 import 해서 재사용한다.
#
# 사용 예:
#   python webtoon_post.py --ep 1 --title "돈보다 비싼 것"          # 컷 수 자동 감지, 초안
#   python webtoon_post.py --ep 1 --title "돈보다 비싼 것" --publish # 바로 공개

GH_DEFAULT = os.environ.get("WEBTOON_GH", "joon-ai-os/joon-webtoon-images")
BLOG_DEFAULT = os.environ.get("WEBTOON_BLOG_ID", "5148798735494731068")
LABELS = ["웹툰", "3분의사치", "로맨스웹툰", "신작웹툰"]

IMG = ('<img src="https://cdn.jsdelivr.net/gh/{gh}@main/{path}{ep:02d}-{n:03d}.png" '
       'alt="{n}컷" style="width:100%; display:block; border:0; margin:0; padding:0;">')


def ep_path(ep, path):
    return path if path else "3minutes-luxury/ep{:02d}/".format(ep)


def count_cuts(gh, path, ep):
    """GitHub 폴더에서 NN-*.png 파일 개수를 세어 컷 수를 자동 감지한다."""
    url = "https://api.github.com/repos/{}/contents/{}".format(gh, path.rstrip("/"))
    r = requests.get(url, params={"ref": "main"}, timeout=30)
    if r.status_code == 404:
        return 0
    r.raise_for_status()
    items = r.json()
    if not isinstance(items, list):
        return 0
    pat = re.compile(r"^{:02d}-\d+\.png$".format(ep))
    return sum(1 for it in items if isinstance(it, dict) and pat.match(it.get("name", "")))


def build_html(ep, title, sub, cuts, gh, path, is_last=False):
    path = ep_path(ep, path)
    if title:
        blog_title = "3분의 사치 · {}화 — {}".format(ep, title)
    else:
        blog_title = "3분의 사치 · {}화".format(ep)
    head_title = title or "3분의 사치"
    imgs = "\n".join(IMG.format(gh=gh, path=path, ep=ep, n=i) for i in range(1, cuts + 1))
    if is_last:
        end_big, end_small = "완결", "그동안 봐주셔서 감사합니다"
    else:
        end_big, end_small = "{}화 끝".format(ep), "다음 화를 기다려 주세요"
    body = """<!-- TITLE: {blog_title} -->
<!-- KEYWORDS: 웹툰, 3분의사치, 로맨스웹툰, 신작웹툰 -->
<div style="max-width:820px; margin:0 auto; background:#ffffff; font-family:'Nanum Gothic','맑은 고딕',sans-serif;">
<div style="text-align:center; padding:24px 16px 16px;">
<div style="font-size:23px; font-weight:800; color:#201e1d;">{head_title}</div>
<div style="font-size:13px; color:#8a8178; margin-top:5px;">{sub}</div>
</div>
{imgs}
<div style="text-align:center; padding:32px 16px 44px;">
<div style="font-size:18px; font-weight:800; color:#201e1d;">{end_big}</div>
<div style="font-size:13px; color:#8a8178; margin-top:6px;">{end_small}</div>
</div>
</div>""".format(blog_title=blog_title, head_title=head_title, sub=sub, imgs=imgs,
                 end_big=end_big, end_small=end_small)
    return blog_title, body


def get_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    r.raise_for_status()
    return r.json()["access_token"]


def post(ep, title, sub, cuts, gh, path, blog, publish, is_last=False):
    """실제 Blogger 투고. (blog_title, url) 반환."""
    blog_title, html = build_html(ep, title, sub, cuts, gh, path, is_last)
    token = get_token()
    body = {"title": blog_title, "content": html, "labels": LABELS}
    params = {} if publish else {"isDraft": "true"}
    r = requests.post(
        "https://www.googleapis.com/blogger/v3/blogs/{}/posts/".format(blog),
        params=params, headers={"Authorization": "Bearer " + token}, json=body,
    )
    if r.status_code >= 300:
        raise SystemExit("투고 실패 {}: {}".format(r.status_code, r.text[:200]))
    j = r.json()
    return blog_title, j.get("url", "(초안)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--cuts", type=int, default=0)  # 0 = 자동 감지
    ap.add_argument("--path", default="")
    ap.add_argument("--gh", default=GH_DEFAULT)
    ap.add_argument("--blog", default=BLOG_DEFAULT)
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()

    path = ep_path(a.ep, a.path)
    sub = a.sub or "{}화".format(a.ep)

    cuts = a.cuts
    if cuts <= 0:
        cuts = count_cuts(a.gh, path, a.ep)
        if cuts <= 0:
            raise SystemExit("컷을 못 찾음: {}/{} 에 {:02d}-###.png 가 없습니다".format(a.gh, path, a.ep))
        print("컷 수 자동 감지:", cuts)

    blog_title, url = post(a.ep, a.title, sub, cuts, a.gh, path, a.blog, a.publish)
    print("공개 완료" if a.publish else "DRAFT 등록 완료")
    print("  제목:", blog_title)
    print("  컷 수:", cuts)
    print("  URL:", url)


if __name__ == "__main__":
    main()
