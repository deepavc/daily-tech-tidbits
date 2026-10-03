"""Daily Tech Tidbits - free-tier AI news agent.
Gathers last-24h AI news from free sources -> Gemini (free tier) writes a <=5 page brief
-> uploads as a Google Doc into the Drive folder "Daily Tech Tidbits"."""
import os, io, time, calendar, datetime as dt
import requests, feedparser, markdown
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

FOLDER_NAME = "Daily Tech Tidbits"
MODELS = [os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), "gemini-2.5-flash-lite"]
PROFILE = ("Beginner-level AI learner who is currently an application developer, "
           "aiming to become an AI developer (LLM apps, RAG, ML/DL, agents, open-source POCs) "
           "and preparing for AI/GenAI developer interviews.")  # <- edit to match your chat

FEEDS = {
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "DeepMind": "https://deepmind.google/blog/rss.xml",
    "LangChain": "https://blog.langchain.dev/rss/",
    "MarkTechPost": "https://www.marktechpost.com/feed/",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
}
HN_QUERIES = ["LLM", "RAG retrieval", "AI agent", "machine learning", "open source AI model"]

def clip(s, n=280):
    return " ".join((s or "").replace("\n", " ").split())[:n]

def gather(hours):
    since = time.time() - hours * 3600
    items = []
    # 1) RSS blogs/news
    for name, url in FEEDS.items():
        try:
            for e in feedparser.parse(url).entries[:15]:
                t = e.get("published_parsed") or e.get("updated_parsed")
                if t and calendar.timegm(t) >= since:
                    items.append(dict(src=name, title=e.title, url=e.link, note=clip(e.get("summary"))))
        except Exception as ex:
            print("feed fail", name, ex)
    # 2) Hacker News (Algolia, free)
    for q in HN_QUERIES:
        try:
            r = requests.get("https://hn.algolia.com/api/v1/search_by_date", timeout=20, params={
                "query": q, "tags": "story", "hitsPerPage": 8,
                "numericFilters": f"created_at_i>{int(since)},points>5"}).json()
            for h in r.get("hits", []):
                items.append(dict(src=f"HN ({h['points']} pts)", title=h["title"],
                                  url=h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}", note=""))
        except Exception as ex:
            print("hn fail", q, ex)
    # 3) arXiv (new papers)
    try:
        feed = feedparser.parse("http://export.arxiv.org/api/query?search_query="
                                "abs:%22retrieval+augmented%22+OR+abs:%22LLM+agent%22+OR+cat:cs.LG"
                                "&sortBy=submittedDate&sortOrder=descending&max_results=12")
        for e in feed.entries:
            items.append(dict(src="arXiv", title=clip(e.title, 150), url=e.link, note=clip(e.summary, 220)))
    except Exception as ex:
        print("arxiv fail", ex)
    # 4) GitHub: new popular repos (open-source POCs)
    try:
        d = (dt.date.today() - dt.timedelta(days=7)).isoformat()
        hdr = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.getenv("GITHUB_TOKEN") else {}
        for topic in ["rag", "llm", "ai-agents"]:
            r = requests.get("https://api.github.com/search/repositories", headers=hdr, timeout=20, params={
                "q": f"topic:{topic} created:>{d}", "sort": "stars", "per_page": 5}).json()
            for g in r.get("items", []):
                items.append(dict(src=f"GitHub ({g['stargazers_count']} stars)", title=g["full_name"],
                                  url=g["html_url"], note=clip(g.get("description"))))
    except Exception as ex:
        print("github fail", ex)
    seen, out = set(), []
    for i in items:
        if i["url"] not in seen:
            seen.add(i["url"]); out.append(i)
    return out

PROMPT = """You are a mentor writing a daily brief for: {profile}
Today is {today}. Below are items gathered from the last ~24 hours (sources: blogs, HN, arXiv, GitHub).

Write a Markdown document of MAX ~1800 words (fits 5 pages). Use ONLY links from the items list - never invent links.
Structure:
# Daily Tech Tidbits - {today}
## 1. Top 5 things that happened (each: 1-2 lines + "Why it matters for you" + [link])
## 2. Learn today (one concept from RAG / ML / DL / LLM tooling that today's items touch; explain simply with a tiny analogy and a 5-line code or pseudo-code idea)
## 3. Open-source POC to try this week (pick 1-2 repos from the list; give a 3-step plan to try it)
## 4. Paper in plain English (1 arXiv item, explained for a beginner in 4-5 lines)
## 5. Interview corner (5 likely interview Q&As linked to today's themes, concise answers)
## 6. Learning path nudge (3 bullets: what to study next, for an app developer moving to AI)
## 7. Links (the ones you used)
Be concrete, beginner-friendly, no hype. If few items exist, say so and fill with evergreen fundamentals.

ITEMS:
{items}
"""

def gemini(prompt):
    key = os.environ["GEMINI_API_KEY"]
    for model in MODELS:
        for attempt in range(4):
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key}, timeout=180,
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.4, "maxOutputTokens": 6000}})
            if r.status_code == 200:
                try:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                except Exception:
                    break
            print(model, r.status_code, r.text[:200])
            if r.status_code in (429, 500, 503):
                time.sleep(20 * (attempt + 1)); continue
            break
    raise RuntimeError("Gemini failed on all models")

def drive():
    creds = Credentials(None, refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["GOOGLE_CLIENT_ID"],
                        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                        scopes=["https://www.googleapis.com/auth/drive.file"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def folder_id(svc):
    q = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = svc.files().list(q=q, fields="files(id)").execute().get("files", [])
    if res:
        return res[0]["id"]
    return svc.files().create(body={"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
                              fields="id").execute()["id"]

def main():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    today = now.strftime("%d %b %Y")
    items = gather(24)
    if len(items) < 10:
        print("few items, widening to 48h"); items = gather(48)
    items = items[:70]
    print(f"{len(items)} items")
    text = "\n".join(f"- [{i['src']}] {i['title']} | {i['url']} | {i['note']}" for i in items)
    md = gemini(PROMPT.format(profile=PROFILE, today=today, items=text))
    html = "<html><body>" + markdown.markdown(md, extensions=["tables", "fenced_code"]) + "</body></html>"
    svc = drive()
    meta = {"name": f"Daily Tech Tidbits - {now.strftime('%Y-%m-%d')}",
            "mimeType": "application/vnd.google-apps.document", "parents": [folder_id(svc)]}
    media = MediaIoBaseUpload(io.BytesIO(html.encode("utf-8")), mimetype="text/html")
    f = svc.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()
    print("Uploaded:", f["webViewLink"])

if __name__ == "__main__":
    main()
