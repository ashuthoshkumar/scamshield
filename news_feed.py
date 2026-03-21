import feedparser
from datetime import datetime

# ── NEWS SOURCES ─────────────────────────────────────────
NEWS_FEEDS = [
    {
        'name': 'Google News - Cyber Scams',
        'url': 'https://news.google.com/rss/search?q=online+scam+cybercrime+india&hl=en-IN&gl=IN&ceid=IN:en'
    },
    {
        'name': 'Google News - Phishing',
        'url': 'https://news.google.com/rss/search?q=phishing+fraud+SMS+scam&hl=en-IN&gl=IN&ceid=IN:en'
    },
    {
        'name': 'Google News - Cyber Crime',
        'url': 'https://news.google.com/rss/search?q=cybercrime+india+2025&hl=en-IN&gl=IN&ceid=IN:en'
    }
]

def get_scam_news(max_articles=10):
    articles = []

    for feed_info in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info['url'])

            for entry in feed.entries[:5]:
                # Get published date
                try:
                    published = entry.published
                    # Parse and reformat date
                    date_obj = datetime(*entry.published_parsed[:6])
                    published = date_obj.strftime("%b %d, %Y %I:%M %p")
                except:
                    published = "Recent"

                # Get summary
                summary = ''
                if hasattr(entry, 'summary'):
                    # Clean HTML tags from summary
                    import re
                    summary = re.sub(r'<[^>]+>', '', entry.summary)
                    summary = summary[:200] + '...' if len(summary) > 200 else summary

                articles.append({
                    'title': entry.title[:100] if entry.title else 'No Title',
                    'link': entry.link,
                    'published': published,
                    'source': feed_info['name'],
                    'summary': summary
                })

        except Exception as e:
            print(f"Error fetching feed {feed_info['name']}: {e}")
            continue

    # Remove duplicates by title
    seen_titles = set()
    unique_articles = []
    for article in articles:
        if article['title'] not in seen_titles:
            seen_titles.add(article['title'])
            unique_articles.append(article)

    return unique_articles[:max_articles]