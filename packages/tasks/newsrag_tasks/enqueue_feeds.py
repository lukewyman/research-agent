# packages/tasks/newsrag_tasks/enqueue_feeds.py
from newsrag_tasks.tasks import fetch_feeds_task
import sys

if __name__ == "__main__":
    feed_group = sys.argv[1] if len(sys.argv) > 1 else "news-live"
    print(f"[+] Enqueuing fetch_feeds_task for feed group: {feed_group}")
    fetch_feeds_task.delay(feed_group)
