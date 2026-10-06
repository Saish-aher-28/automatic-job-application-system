"""
adapter.py — Website crawlers source adapter for static HTML scraping.
"""

from __future__ import annotations
import urllib.request
import urllib.parse
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

from phase_6.config.config import config
from phase_6.sources.base import JobSource, RawJobItem

logger = logging.getLogger(__name__)


class WebsiteSource(JobSource):
    """
    Crawls configured job board websites.
    Parses listing pages and individual job post details using BeautifulSoup.
    """

    def __init__(self, sources_config: List[Dict[str, Any]] = None):
        # Allow passing config dynamically, or load from environment (config.WEBSITE_SOURCES),
        # or fallback to a localhost mock config for development use.
        if sources_config is not None:
            self.sources_config = sources_config
        elif config.WEBSITE_SOURCES:
            self.sources_config = config.WEBSITE_SOURCES
        else:
            # Development scaffold: mock server. Set WEBSITE_SOURCES env var for production.
            self.sources_config = [
                {
                    "name": "Static Mock Job Board",
                    "base_url": "http://localhost:18083/mock-jobs",
                    "listing_url": "http://localhost:18083/mock-jobs/list.html",
                    "enabled": True
                }
            ]

    def fetch(self) -> List[RawJobItem]:
        """
        Crawls listing URLs and extracts raw text for job items.
        """
        raw_items = []

        for site in self.sources_config:
            if not site.get("enabled", True):
                continue

            name = site.get("name")
            listing_url = site.get("listing_url")
            base_url = site.get("base_url")

            logger.info(f"Crawling website source: {name} ({listing_url})")

            try:
                # 1. Fetch listing page (try primary listing_url, and if no detail links found, check /jobs/ section)
                listing_html = self._fetch_url(listing_url)
                soup = BeautifulSoup(listing_html or "", "html.parser")
                detail_links = self._extract_detail_links(soup, base_url or listing_url)

                if not detail_links and listing_url and not listing_url.endswith("/jobs/"):
                    alt_url = urllib.parse.urljoin(listing_url, "/jobs/")
                    alt_html = self._fetch_url(alt_url)
                    if alt_html:
                        alt_soup = BeautifulSoup(alt_html, "html.parser")
                        detail_links = self._extract_detail_links(alt_soup, alt_url)

                logger.info(f"Discovered {len(detail_links)} job links on {name}.")

                # 3. Crawl each job detail page
                # Limit to config.MAX_PAGES to avoid rate limiting
                for idx, url in enumerate(detail_links[:config.MAX_PAGES]):
                    logger.info(f"Fetching job detail page [{idx+1}]: {url}")
                    detail_html = self._fetch_url(url)
                    if not detail_html:
                        continue

                    # Extract job post content
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    raw_text = self._extract_job_text(detail_soup)
                    
                    if not raw_text or not raw_text.strip():
                        continue

                    raw_item = RawJobItem(
                        source="website",
                        source_type="static_crawl",
                        source_name=name,
                        source_url=url,
                        raw_text=raw_text
                    )
                    raw_items.append(raw_item)

            except Exception as e:
                logger.error(f"Error crawling website source {name}: {e}")
                # Don't fail the entire ingestion run for one site failure
                continue

        return raw_items

    def _fetch_url(self, url: str) -> Optional[str]:
        """Fetches HTML content of a URL with timeouts and standard User-Agent headers."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Phase6IngestionBot/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to fetch URL {url}: {e}")
            return None

    def _extract_detail_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Heuristic details link extractor.
        Looks for standard links that are likely to be job listings.
        """
        links = []
        ignored_patterns = ["/contact", "/blog", "/pricing", "/terms", "/privacy", "/mentors", "/course", "/pro-courses", "/ai-tools", "/walk-in-drive", "/page/", "/category/", "/author/"]
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("#") or "javascript:" in href or href.startswith("mailto:"):
                continue
                
            full_url = urllib.parse.urljoin(base_url, href)
            path = urllib.parse.urlparse(full_url).path.lower()
            
            # Skip root/home or known static non-job pages
            if path in ["", "/", "/jobs", "/jobs/"]:
                continue
            if any(ign in path for ign in ignored_patterns):
                continue

            # Identify candidate job detail URLs
            if "/job" in path or "/career" in path or "-job-" in path or "opening-in-" in path or "-hiring-" in path or (href.endswith(".html") and href != "list.html"):
                links.append(full_url)
            elif len(path.strip("/").split("/")) == 1 and len(path.strip("/")) > 10:
                # Single-level blog/job slug on WordPress
                links.append(full_url)
                
        # Deduplicate
        return list(dict.fromkeys(links))

    def _extract_job_text(self, soup: BeautifulSoup) -> str:
        """
        Extracts the main textual body of the job post page.
        """
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Find typical job detail container selectors
        # Fallback to main body text if specific containers aren't found
        container = soup.find(id="job-detail") or soup.find(class_="job-post") or soup.find("article") or soup.find("body")
        if container:
            # Get text and format spacing
            lines = (line.strip() for line in container.get_text().splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(chunk for chunk in chunks if chunk)
        return ""
