"""
Curated high-quality seed vacancies across Ukraine, Europe, and the USA.
Used for ground-truth testing, initial platform discovery, and AI matching evaluations.
"""
from typing import List, Dict, Any

SEED_JOBS: List[Dict[str, Any]] = [
    # --- Ukraine (UA) ---
    {
        "external_id": "seed-ua-kyivstar-001",
        "title": "Senior Android Engineer",
        "company_name": "KyivStar",
        "location": "Kyiv, Ukraine (Hybrid / Remote)",
        "region": "UA",
        "raw_description": (
            "KyivStar is looking for a Senior Android Engineer to lead our digital self-care products serving millions of users. "
            "You will architect new features using Jetpack Compose, Kotlin Coroutines, and modern MVI architecture. "
            "Requirements: 4+ years of Android development with Kotlin, deep knowledge of Coroutines/Flow, Room, and Clean Architecture. "
            "Experience with modularization, CI/CD with GitHub Actions, and unit/UI testing."
        ),
        "required_skills": ["Kotlin", "Android SDK", "Jetpack Compose", "Coroutines", "Flow", "Clean Architecture"],
        "preferred_skills": ["KMP", "Hilt", "Room", "CI/CD"],
        "min_experience_years": 4.0,
        "salary_min": 4500,
        "salary_max": 6000,
        "salary_currency": "USD",
        "source_url": "https://dou.ua/companies/kyivstar/vacancies/",
    },
    {
        "external_id": "seed-ua-grammarly-002",
        "title": "Staff Android Engineer (Core Engine)",
        "company_name": "Grammarly",
        "location": "Kyiv, Ukraine / Remote",
        "region": "UA",
        "raw_description": (
            "Grammarly’s mobile team is building next-generation writing assistance for hundreds of millions of daily keystrokes. "
            "We seek a Staff Android Engineer to optimize low-latency on-device processing and text input rendering. "
            "Requirements: 6+ years in Android, mastery of memory profiling, low-latency IPC, custom View rendering, and NDK/C++ interoperability. "
            "Background in AI on-device inference or keyboard IME services is a major plus."
        ),
        "required_skills": ["Kotlin", "Android SDK", "Performance Profiling", "Coroutines", "NDK", "System Architecture"],
        "preferred_skills": ["On-device AI", "C++", "IME Services", "Jetpack Compose"],
        "min_experience_years": 6.0,
        "salary_min": 7000,
        "salary_max": 9500,
        "salary_currency": "USD",
        "source_url": "https://www.grammarly.com/jobs",
    },
    {
        "external_id": "seed-ua-preply-003",
        "title": "Senior AI & Backend Engineer",
        "company_name": "Preply",
        "location": "Kyiv, Ukraine (Remote friendly)",
        "region": "UA",
        "raw_description": (
            "Join Preply's AI team building interactive language learning assistants and automated tutor matching. "
            "You will build production-grade LLM workflows using Python, FastAPI, LangChain, and PostgreSQL with pgvector. "
            "Requirements: 4+ years Python experience, FastAPI, asynchronous programming, LangChain / LangGraph, RAG architecture, "
            "and PostgreSQL. Knowledge of prompt evaluation and observability (Langfuse) highly desired."
        ),
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "LangChain", "RAG", "Embeddings"],
        "preferred_skills": ["pgvector", "LangGraph", "Docker", "Langfuse", "Redis"],
        "min_experience_years": 4.0,
        "salary_min": 5000,
        "salary_max": 7000,
        "salary_currency": "USD",
        "source_url": "https://preply.com/en/jobs",
    },
    {
        "external_id": "seed-ua-softserve-004",
        "title": "Lead Python / Cloud Architect",
        "company_name": "SoftServe",
        "location": "Lviv, Ukraine / Remote",
        "region": "UA",
        "raw_description": (
            "SoftServe is looking for a Lead Python Developer to architect cloud-native solutions for healthcare and enterprise clients. "
            "Must have extensive experience with FastAPI, SQLAlchemy 2.0, PostgreSQL, Celery, and AWS/GCP deployments. "
            "Strong grasp of microservices vs modular monoliths, DDD, Docker Compose, and CI/CD pipelines."
        ),
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "Docker", "AWS"],
        "preferred_skills": ["Celery", "Redis", "Terraform", "Kubernetes"],
        "min_experience_years": 5.0,
        "salary_min": 5500,
        "salary_max": 7500,
        "salary_currency": "USD",
        "source_url": "https://career.softserveinc.com",
    },

    # --- Europe (EU) ---
    {
        "external_id": "seed-eu-spotify-005",
        "title": "Senior Android Engineer (Player UI)",
        "company_name": "Spotify",
        "location": "Stockholm, Sweden / London, UK",
        "region": "EU",
        "raw_description": (
            "Spotify is seeking a Senior Android Engineer to craft delightful listening experiences across our mobile ecosystem. "
            "You will collaborate on complex animations, real-time media streaming playback, and large-scale A/B experiments. "
            "Requirements: 5+ years of production Android engineering, expert Kotlin skills, Jetpack Compose, reactive streams (Flow/RxJava), "
            "and architecture design for apps with 500M+ installs."
        ),
        "required_skills": ["Kotlin", "Android SDK", "Jetpack Compose", "Coroutines", "ExoPlayer", "Clean Architecture"],
        "preferred_skills": ["KMP", "Design Systems", "Media Streaming", "A/B Testing"],
        "min_experience_years": 5.0,
        "salary_min": 85000,
        "salary_max": 115000,
        "salary_currency": "EUR",
        "source_url": "https://www.lifeatspotify.com/jobs",
    },
    {
        "external_id": "seed-eu-revolut-006",
        "title": "Senior Mobile Security & Android Engineer",
        "company_name": "Revolut",
        "location": "London, UK / Warsaw, Poland",
        "region": "EU",
        "raw_description": (
            "Revolut is looking for a high-performing Android Engineer focused on banking security, biometric auth, and core payments. "
            "You will build tamper-resistant financial flows, biometric cryptographic handshakes, and high-reliability offline caches. "
            "Requirements: 4+ years Android, deep knowledge of cryptography/KeyStore, Kotlin, SQLite/Room, and modular architectures."
        ),
        "required_skills": ["Kotlin", "Android SDK", "Cryptography", "Security", "Room", "Coroutines"],
        "preferred_skills": ["NDK", "KeyStore", "MVI", "Hilt"],
        "min_experience_years": 4.0,
        "salary_min": 75000,
        "salary_max": 105000,
        "salary_currency": "EUR",
        "source_url": "https://www.revolut.com/careers",
    },
    {
        "external_id": "seed-eu-deliveryhero-007",
        "title": "Senior Backend Engineer (Python & AsyncIO)",
        "company_name": "Delivery Hero",
        "location": "Berlin, Germany",
        "region": "EU",
        "raw_description": (
            "Delivery Hero operates delivery platforms in 70+ countries. We need a Senior Backend Engineer to maintain dispatch order pipelines. "
            "Requirements: 4+ years of Python (FastAPI/AsyncIO), PostgreSQL optimization, distributed caching with Redis, message brokers (Kafka/RabbitMQ), "
            "and observability with OpenTelemetry."
        ),
        "required_skills": ["Python", "FastAPI", "AsyncIO", "PostgreSQL", "Redis", "Docker"],
        "preferred_skills": ["Kafka", "OpenTelemetry", "Kubernetes", "AWS"],
        "min_experience_years": 4.0,
        "salary_min": 80000,
        "salary_max": 100000,
        "salary_currency": "EUR",
        "source_url": "https://careers.deliveryhero.com",
    },

    # --- United States (US) ---
    {
        "external_id": "seed-us-stripe-008",
        "title": "Senior Mobile Platform Engineer",
        "company_name": "Stripe",
        "location": "San Francisco, CA / US Remote",
        "region": "US",
        "raw_description": (
            "Stripe Terminal and Payments SDK empowers millions of developers worldwide. We are looking for a Senior Mobile Engineer "
            "to build bulletproof SDKs and hardware POS terminal applications on Android. "
            "Requirements: 5+ years of Android development with Kotlin/Java, public API design experience, Bluetooth/NFC hardware integration, "
            "and rigorous automated testing."
        ),
        "required_skills": ["Kotlin", "Android SDK", "SDK Design", "Coroutines", "Security", "Testing"],
        "preferred_skills": ["Bluetooth Low Energy", "NFC", "Hardware POS", "Gradle Plugins"],
        "min_experience_years": 5.0,
        "salary_min": 175000,
        "salary_max": 230000,
        "salary_currency": "USD",
        "source_url": "https://stripe.com/jobs",
    },
    {
        "external_id": "seed-us-openai-009",
        "title": "AI Application Platform Engineer",
        "company_name": "OpenAI",
        "location": "San Francisco, CA",
        "region": "US",
        "raw_description": (
            "Help build the interfaces, agents, and infrastructure that power ChatGPT and Developer APIs. "
            "We are looking for engineers with deep experience in Python, FastAPI, state machines, vector databases, and evaluation frameworks. "
            "Requirements: 4+ years experience with high-performance Python, LLM orchestration, Model Context Protocol (MCP), and distributed systems."
        ),
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Vector Databases", "LLM APIs", "System Architecture"],
        "preferred_skills": ["MCP", "LangGraph", "DeepEval", "Redis", "Distributed Systems"],
        "min_experience_years": 4.0,
        "salary_min": 210000,
        "salary_max": 290000,
        "salary_currency": "USD",
        "source_url": "https://openai.com/careers",
    },
    {
        "external_id": "seed-us-airbnb-010",
        "title": "Staff Android Engineer (Design Systems)",
        "company_name": "Airbnb",
        "location": "New York, NY / US Remote",
        "region": "US",
        "raw_description": (
            "Airbnb’s mobile apps define quality standards in the tech industry. As a Staff Android Engineer on Design Systems, "
            "you will architect our universal UI component library in Jetpack Compose, build accessibility tools, and mentor mobile engineers. "
            "Requirements: 6+ years Android engineering, mastery of Jetpack Compose internals, custom layout measure/layout passes, "
            "and multi-module Gradle architecture."
        ),
        "required_skills": ["Kotlin", "Jetpack Compose", "Design Systems", "Android SDK", "Architecture", "Accessibility"],
        "preferred_skills": ["Compose Compiler", "Figma Plugins", "Screen Reader APIs", "KMP"],
        "min_experience_years": 6.0,
        "salary_min": 190000,
        "salary_max": 250000,
        "salary_currency": "USD",
        "source_url": "https://careers.airbnb.com",
    },

    # --- Global Remote ---
    {
        "external_id": "seed-remote-gitlab-011",
        "title": "Senior Backend Engineer (AI Features)",
        "company_name": "GitLab",
        "location": "Remote - Global",
        "region": "REMOTE",
        "raw_description": (
            "GitLab Duo is bringing AI-assisted coding and automated workflows to our DevSecOps platform. "
            "We seek a Senior Python / Backend Engineer to build scalable agentic pipelines and code explanation tools. "
            "Requirements: 4+ years in modern Python (FastAPI/asyncio), experience integrating LLMs and vector embeddings, "
            "PostgreSQL performance tuning, and asynchronous background queues with Celery/Redis."
        ),
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "RAG", "Embeddings", "Docker"],
        "preferred_skills": ["Celery", "Redis", "OpenTelemetry", "CI/CD"],
        "min_experience_years": 4.0,
        "salary_min": 120000,
        "salary_max": 160000,
        "salary_currency": "USD",
        "source_url": "https://about.gitlab.com/jobs",
    },
]
