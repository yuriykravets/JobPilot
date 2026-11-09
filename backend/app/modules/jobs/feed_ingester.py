import asyncio
import html
import re
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.schemas import JobCreateSchema, JobRegion
from app.modules.jobs.service import upsert_job

logger = logging.getLogger(__name__)

USER_AGENT = "JobPilot-AI-Engine/1.0 (+https://github.com/jobpilot)"


def clean_html_text(raw_html: str) -> str:
    """Strips HTML tags, unescapes HTML entities, and collapses redundant whitespace."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    return " ".join(text.split()).strip()


def parse_salary_string(salary_str: Optional[str]) -> tuple[Optional[int], Optional[int], str]:
    """
    Extracts numerical min and max salary and currency from strings like '$80k - $120k' or '$3,500 - $5,000/month'.
    """
    if not salary_str:
        return None, None, "USD"

    currency = "EUR" if "€" in salary_str else "UAH" if "грн" in salary_str or "₴" in salary_str else "USD"

    # Find numbers
    numbers = re.findall(r"(\d+(?:[.,]\d+)?)\s*(k|K)?", salary_str)
    parsed_nums = []
    for num_str, multiplier in numbers:
        try:
            val = float(num_str.replace(",", ""))
            if multiplier:
                val *= 1000
            parsed_nums.append(int(val))
        except ValueError:
            continue

    if len(parsed_nums) >= 2:
        return min(parsed_nums[0], parsed_nums[1]), max(parsed_nums[0], parsed_nums[1]), currency
    elif len(parsed_nums) == 1:
        return parsed_nums[0], None, currency
    return None, None, currency


async def fetch_dou_jobs(categories: List[str] = ["Android", "Python"]) -> List[JobCreateSchema]:
    """
    Fetches real active developer vacancies for Ukraine directly from the official DOU.ua RSS feeds.
    """
    jobs: List[JobCreateSchema] = []
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
        for cat in categories:
            url = f"https://jobs.dou.ua/vacancies/feeds/?category={cat}"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning(f"DOU.ua feed '{cat}' returned status {resp.status_code}")
                    continue

                root = ET.fromstring(resp.content)
                items = root.findall(".//item")

                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    guid_elem = item.find("guid")

                    raw_title = title_elem.text if title_elem is not None and title_elem.text else f"{cat} Developer"
                    link = link_elem.text if link_elem is not None and link_elem.text else ""
                    raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                    cleaned_desc = clean_html_text(raw_desc)
                    if len(cleaned_desc) < 30:
                        cleaned_desc = f"{raw_title} vacancy on DOU.ua. Read full description and apply directly on DOU."

                    # Parse DOU title format: '{Role} в {Company}, {Location}'
                    role = raw_title
                    company = "Ukrainian Tech Company"
                    location = "Ukraine (Remote / Hybrid)"

                    if " в " in raw_title:
                        parts = raw_title.split(" в ", 1)
                        role = parts[0].strip()
                        company_loc = parts[1].strip()
                        if ", " in company_loc:
                            company_parts = company_loc.rsplit(", ", 1)
                            company = company_parts[0].strip()
                            location = f"{company_parts[1].strip()}, Ukraine"
                        else:
                            company = company_loc

                    # Derive external_id from link
                    match = re.search(r"/vacancies/(\d+)/", link)
                    ext_id = f"dou-{match.group(1)}" if match else f"dou-{abs(hash(link)) % 1000000}"

                    # Detect skills from description and category
                    skills = [cat]
                    if cat.lower() == "android":
                        skills.extend(["Kotlin", "Android SDK"])
                        if "compose" in cleaned_desc.lower():
                            skills.append("Jetpack Compose")
                        if "coroutines" in cleaned_desc.lower():
                            skills.append("Coroutines")
                    elif cat.lower() == "python":
                        skills.append("Python")
                        if "fastapi" in cleaned_desc.lower():
                            skills.append("FastAPI")
                        if "postgres" in cleaned_desc.lower() or "postgresql" in cleaned_desc.lower():
                            skills.append("PostgreSQL")

                    job_schema = JobCreateSchema(
                        title=role,
                        company_name=company,
                        location=location,
                        region=JobRegion.UA,
                        raw_description=cleaned_desc,
                        required_skills=skills[:6],
                        preferred_skills=["Git", "REST APIs"],
                        min_experience_years=3.0,
                        salary_currency="USD",
                        source_url=link,
                        external_id=ext_id,
                    )
                    jobs.append(job_schema)

            except Exception as e:
                logger.error(f"Error fetching DOU.ua feed for '{cat}': {e}")

    return jobs


async def fetch_remotive_jobs(limit: int = 25) -> List[JobCreateSchema]:
    """
    Fetches real active software engineering jobs across Europe, USA, and Remote from the Remotive public API.
    """
    jobs: List[JobCreateSchema] = []
    headers = {"User-Agent": USER_AGENT}
    url = f"https://remotive.com/api/remote-jobs?category=software-dev&limit={limit}"

    async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Remotive API returned status {resp.status_code}")
                return jobs

            data = resp.json()
            raw_jobs = data.get("jobs", [])

            for item in raw_jobs:
                title = item.get("title", "Software Engineer")
                company = item.get("company_name", "Global Tech")
                location_str = item.get("candidate_required_location", "Worldwide")
                cleaned_desc = clean_html_text(item.get("description", ""))
                if len(cleaned_desc) < 30:
                    cleaned_desc = f"{title} at {company}. Apply directly at original source."

                # Determine geographical region
                loc_lower = location_str.lower()
                if "usa" in loc_lower or "us only" in loc_lower or "united states" in loc_lower:
                    region = JobRegion.US
                elif "europe" in loc_lower or "uk" in loc_lower or "germany" in loc_lower or "eu" in loc_lower:
                    region = JobRegion.EU
                else:
                    region = JobRegion.REMOTE

                # Parse salary
                salary_min, salary_max, currency = parse_salary_string(item.get("salary"))

                # Tags / Skills
                raw_tags = item.get("tags", [])
                skills = [t.title() for t in raw_tags if len(t) > 1 and len(t) < 25][:8]
                if not skills:
                    skills = ["Software Engineering", "Fullstack"]

                job_schema = JobCreateSchema(
                    title=title,
                    company_name=company,
                    location=f"Remote ({location_str})",
                    region=region,
                    raw_description=cleaned_desc,
                    required_skills=skills[:6],
                    preferred_skills=skills[6:] if len(skills) > 6 else ["Docker", "Git"],
                    min_experience_years=3.0,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=currency,
                    source_url=item.get("url"),
                    external_id=f"remotive-{item.get('id')}",
                )
                jobs.append(job_schema)

        except Exception as e:
            logger.error(f"Error fetching Remotive API jobs: {e}")

    return jobs


async def sync_all_live_feeds(db: AsyncSession) -> Dict[str, Any]:
    """
    Coordinates simultaneous fetching from Ukrainian (DOU.ua) and Global (Remotive) live feeds
    and upserts all jobs into PostgreSQL.
    """
    logger.info("Starting live job feeds synchronization...")
    
    # Fetch feeds concurrently using asyncio.gather
    dou_task = fetch_dou_jobs(categories=["Android", "Python"])
    remotive_task = fetch_remotive_jobs(limit=25)

    dou_jobs, remotive_jobs = await asyncio.gather(dou_task, remotive_task, return_exceptions=True)

    dou_list = dou_jobs if isinstance(dou_jobs, list) else []
    remotive_list = remotive_jobs if isinstance(remotive_jobs, list) else []

    all_jobs = dou_list + remotive_list
    synced_count = 0

    for job_schema in all_jobs:
        try:
            await upsert_job(job_schema, db)
            synced_count += 1
        except Exception as e:
            logger.error(f"Failed to upsert job {job_schema.external_id}: {e}")

    return {
        "status": "success",
        "total_synced": synced_count,
        "dou_ua_count": len(dou_list),
        "remotive_global_count": len(remotive_list),
        "message": f"Successfully synced {synced_count} live vacancies (Ukraine: {len(dou_list)}, Europe/US/Remote: {len(remotive_list)}).",
    }
