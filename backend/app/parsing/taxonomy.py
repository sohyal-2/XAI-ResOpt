"""Comprehensive taxonomy, normalization dictionaries, and synonym graphs for technical skills, tooling, domains, certifications, and job requirements."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TaxonomyEntry:
    pattern: str
    canonical: str
    display_name: str
    synonyms: tuple[str, ...]
    category: str = "skill"


# Comprehensive mapping of patterns -> canonical slug, display name, synonyms, and default category
TECH_TAXONOMY: list[TaxonomyEntry] = [
    # Frontend / JavaScript ecosystem
    TaxonomyEntry(r"react(?:\.js|js)?", "react", "React", ("React", "React.js", "ReactJS", "React.js library"), "skill"),
    TaxonomyEntry(r"react\s*native", "react_native", "React Native", ("React Native", "ReactNative"), "skill"),
    TaxonomyEntry(r"next(?:\.js|js)?", "next.js", "Next.js", ("Next.js", "NextJS", "Next"), "skill"),
    TaxonomyEntry(r"vue(?:\.js|js)?", "vue", "Vue.js", ("Vue", "Vue.js", "VueJS", "Vue 3"), "skill"),
    TaxonomyEntry(r"nuxt(?:\.js|js)?", "nuxt", "Nuxt.js", ("Nuxt", "Nuxt.js", "NuxtJS"), "skill"),
    TaxonomyEntry(r"angular(?:\.js|js)?", "angular", "Angular", ("Angular", "AngularJS", "Angular 2+"), "skill"),
    TaxonomyEntry(r"svelte(?:kit)?", "svelte", "Svelte", ("Svelte", "SvelteKit"), "skill"),
    TaxonomyEntry(r"node(?:\.js|js)?", "node.js", "Node.js", ("Node.js", "NodeJS", "Node"), "skill"),
    TaxonomyEntry(r"javascript|(?<![a-zA-Z0-9_])js(?![a-zA-Z0-9_])|ecmascript|es6\+?", "javascript", "JavaScript", ("JavaScript", "JS", "ECMAScript", "ES6+"), "skill"),
    TaxonomyEntry(r"typescript|(?<![a-zA-Z0-9_])ts(?![a-zA-Z0-9_])", "typescript", "TypeScript", ("TypeScript", "TS"), "skill"),
    TaxonomyEntry(r"html5?|html", "html", "HTML5", ("HTML", "HTML5"), "skill"),
    TaxonomyEntry(r"css3?|css", "css", "CSS3", ("CSS", "CSS3"), "skill"),
    TaxonomyEntry(r"tailwind(?:\s*css)?", "tailwind_css", "Tailwind CSS", ("Tailwind CSS", "TailwindCSS", "Tailwind"), "tooling"),
    TaxonomyEntry(r"sass|scss", "sass", "Sass / SCSS", ("Sass", "SCSS"), "tooling"),
    TaxonomyEntry(r"webpack", "webpack", "Webpack", ("Webpack", "Module Bundler"), "tooling"),
    TaxonomyEntry(r"vite", "vite", "Vite", ("Vite", "ViteJS"), "tooling"),
    TaxonomyEntry(r"redux(?:-toolkit)?", "redux", "Redux", ("Redux", "Redux Toolkit", "RTK"), "skill"),
    TaxonomyEntry(r"zustand", "zustand", "Zustand", ("Zustand",), "skill"),

    # Backend languages & frameworks
    TaxonomyEntry(r"python3?|python", "python", "Python", ("Python", "Python 3", "Python3"), "skill"),
    TaxonomyEntry(r"fastapi", "fastapi", "FastAPI", ("FastAPI",), "skill"),
    TaxonomyEntry(r"flask", "flask", "Flask", ("Flask",), "skill"),
    TaxonomyEntry(r"django", "django", "Django", ("Django", "Django REST Framework", "DRF"), "skill"),
    TaxonomyEntry(r"express(?:\.js|js)?", "express", "Express.js", ("Express", "Express.js", "ExpressJS"), "skill"),
    TaxonomyEntry(r"nestjs", "nestjs", "NestJS", ("NestJS", "Nest.js"), "skill"),
    TaxonomyEntry(r"golang|(?<![a-zA-Z0-9_])go(?![a-zA-Z0-9_])", "golang", "Go / Golang", ("Go", "Golang"), "skill"),
    TaxonomyEntry(r"rust", "rust", "Rust", ("Rust", "Rustlang"), "skill"),
    TaxonomyEntry(r"java(?!\s*script)", "java", "Java", ("Java", "Java 17", "Java 21", "Core Java"), "skill"),
    TaxonomyEntry(r"spring(?:\s*boot)?", "spring_boot", "Spring Boot", ("Spring", "Spring Boot", "Spring Framework"), "skill"),
    TaxonomyEntry(r"c\+\+|cpp", "cpp", "C++", ("C++", "CPP", "Modern C++"), "skill"),
    TaxonomyEntry(r"c#|csharp", "csharp", "C#", ("C#", "CSharp", ".NET C#"), "skill"),
    TaxonomyEntry(r"\.net(?:\s*core)?|dotnet", "dotnet", ".NET", (".NET", ".NET Core", "DotNet"), "skill"),
    TaxonomyEntry(r"ruby(?:\s*on\s*rails)?|rails", "ruby_on_rails", "Ruby on Rails", ("Ruby", "Ruby on Rails", "Rails"), "skill"),
    TaxonomyEntry(r"php", "php", "PHP", ("PHP", "Modern PHP"), "skill"),
    TaxonomyEntry(r"laravel", "laravel", "Laravel", ("Laravel",), "skill"),
    TaxonomyEntry(r"scala", "scala", "Scala", ("Scala",), "skill"),
    TaxonomyEntry(r"kotlin", "kotlin", "Kotlin", ("Kotlin",), "skill"),
    TaxonomyEntry(r"swift", "swift", "Swift", ("Swift", "SwiftUI"), "skill"),

    # Databases & Caching
    TaxonomyEntry(r"postgres(?:ql)?|pgsql", "postgresql", "PostgreSQL", ("Postgres", "PostgreSQL", "PGSQL"), "skill"),
    TaxonomyEntry(r"mysql", "mysql", "MySQL", ("MySQL",), "skill"),
    TaxonomyEntry(r"sqlite", "sqlite", "SQLite", ("SQLite",), "skill"),
    TaxonomyEntry(r"mongodb|mongo", "mongodb", "MongoDB", ("MongoDB", "Mongo"), "skill"),
    TaxonomyEntry(r"redis", "redis", "Redis", ("Redis", "Redis Cache"), "skill"),
    TaxonomyEntry(r"cassandra", "cassandra", "Apache Cassandra", ("Cassandra", "Apache Cassandra"), "skill"),
    TaxonomyEntry(r"dynamodb", "dynamodb", "Amazon DynamoDB", ("DynamoDB", "Amazon DynamoDB"), "skill"),
    TaxonomyEntry(r"elasticsearch|opensearch", "elasticsearch", "Elasticsearch / OpenSearch", ("Elasticsearch", "OpenSearch", "Elastic"), "skill"),
    TaxonomyEntry(r"pgvector", "pgvector", "pgvector", ("pgvector", "PostgreSQL Vector"), "skill"),
    TaxonomyEntry(r"snowflake", "snowflake", "Snowflake", ("Snowflake", "Snowflake Data Warehouse"), "skill"),
    TaxonomyEntry(r"bigquery", "bigquery", "Google BigQuery", ("BigQuery", "Google BigQuery"), "skill"),
    TaxonomyEntry(r"clickhouse", "clickhouse", "ClickHouse", ("ClickHouse",), "skill"),
    TaxonomyEntry(r"sql", "sql", "SQL", ("SQL", "Relational Databases", "RDBMS"), "skill"),
    TaxonomyEntry(r"nosql", "nosql", "NoSQL", ("NoSQL", "Document Stores"), "skill"),

    # Cloud & DevOps / Tooling
    TaxonomyEntry(r"aws|amazon\s+web\s+services", "aws", "AWS", ("AWS", "Amazon Web Services", "Amazon Cloud"), "skill"),
    TaxonomyEntry(r"gcp|google\s+cloud(?:\s+platform)?", "gcp", "Google Cloud", ("GCP", "Google Cloud", "Google Cloud Platform"), "skill"),
    TaxonomyEntry(r"azure|microsoft\s+azure", "azure", "Microsoft Azure", ("Azure", "Microsoft Azure"), "skill"),
    TaxonomyEntry(r"docker", "docker", "Docker", ("Docker", "Containerization", "Containers"), "tooling"),
    TaxonomyEntry(r"kubernetes|k8s", "kubernetes", "Kubernetes", ("Kubernetes", "K8s", "Container Orchestration"), "tooling"),
    TaxonomyEntry(r"terraform", "terraform", "Terraform", ("Terraform", "Infrastructure as Code", "IaC"), "tooling"),
    TaxonomyEntry(r"ansible", "ansible", "Ansible", ("Ansible",), "tooling"),
    TaxonomyEntry(r"helm", "helm", "Helm", ("Helm", "Helm Charts"), "tooling"),
    TaxonomyEntry(r"ci[\s/-]?cd|continuous\s+integration|continuous\s+deployment", "ci_cd", "CI/CD", ("CI/CD", "Continuous Integration", "Continuous Deployment", "Pipelines"), "tooling"),
    TaxonomyEntry(r"github\s*actions", "github_actions", "GitHub Actions", ("GitHub Actions", "GHA"), "tooling"),
    TaxonomyEntry(r"gitlab\s*ci", "gitlab_ci", "GitLab CI", ("GitLab CI", "GitLab CI/CD"), "tooling"),
    TaxonomyEntry(r"jenkins", "jenkins", "Jenkins", ("Jenkins",), "tooling"),
    TaxonomyEntry(r"git|github|gitlab", "git", "Git / Version Control", ("Git", "GitHub", "GitLab", "Version Control"), "tooling"),
    TaxonomyEntry(r"linux|unix|ubuntu", "linux", "Linux", ("Linux", "Unix", "Ubuntu", "POSIX"), "tooling"),
    TaxonomyEntry(r"datadog", "datadog", "Datadog", ("Datadog", "APM"), "tooling"),
    TaxonomyEntry(r"prometheus", "prometheus", "Prometheus", ("Prometheus", "Metrics"), "tooling"),
    TaxonomyEntry(r"grafana", "grafana", "Grafana", ("Grafana", "Observability"), "tooling"),
    TaxonomyEntry(r"jira", "jira", "Jira", ("Jira", "Atlassian Jira"), "tooling"),

    # AI / ML / LLM
    TaxonomyEntry(r"machine\s*learning|(?<![a-zA-Z0-9_])ml(?![a-zA-Z0-9_])", "machine_learning", "Machine Learning", ("Machine Learning", "ML", "Statistical Learning"), "skill"),
    TaxonomyEntry(r"deep\s*learning|(?<![a-zA-Z0-9_])dl(?![a-zA-Z0-9_])", "deep_learning", "Deep Learning", ("Deep Learning", "DL", "Neural Networks"), "skill"),
    TaxonomyEntry(r"natural\s+language\s+processing|(?<![a-zA-Z0-9_])nlp(?![a-zA-Z0-9_])", "nlp", "NLP", ("NLP", "Natural Language Processing", "Text Processing"), "skill"),
    TaxonomyEntry(r"large\s+language\s+models?|(?<![a-zA-Z0-9_])llms?(?![a-zA-Z0-9_])|generative\s+ai|genai", "llm", "Large Language Models", ("LLM", "LLMs", "Large Language Models", "Generative AI", "GenAI"), "skill"),
    TaxonomyEntry(r"langchain", "langchain", "LangChain", ("LangChain",), "tooling"),
    TaxonomyEntry(r"langgraph", "langgraph", "LangGraph", ("LangGraph",), "tooling"),
    TaxonomyEntry(r"llamaindex", "llamaindex", "LlamaIndex", ("LlamaIndex",), "tooling"),
    TaxonomyEntry(r"rag|retrieval[- ]augmented\s+generation|agentic\s+rag", "rag", "RAG", ("RAG", "Retrieval-Augmented Generation", "Agentic RAG"), "skill"),
    TaxonomyEntry(r"pytorch", "pytorch", "PyTorch", ("PyTorch", "Torch"), "tooling"),
    TaxonomyEntry(r"tensorflow", "tensorflow", "TensorFlow", ("TensorFlow", "TF"), "tooling"),
    TaxonomyEntry(r"scikit-learn|sklearn", "scikit_learn", "Scikit-Learn", ("Scikit-Learn", "sklearn"), "tooling"),
    TaxonomyEntry(r"pandas", "pandas", "Pandas", ("Pandas",), "tooling"),
    TaxonomyEntry(r"numpy", "numpy", "NumPy", ("NumPy",), "tooling"),
    TaxonomyEntry(r"hugging\s*face|transformers", "huggingface", "Hugging Face", ("Hugging Face", "Transformers"), "tooling"),

    # Architecture & API Concepts / Keywords
    TaxonomyEntry(r"rest(?:ful)?(?:\s+apis?)?|api|apis", "rest_api", "REST APIs", ("REST", "RESTful", "REST API", "RESTful APIs", "API", "APIs"), "keyword"),
    TaxonomyEntry(r"graphql", "graphql", "GraphQL", ("GraphQL", "GraphQL API"), "skill"),
    TaxonomyEntry(r"grpc", "grpc", "gRPC", ("gRPC", "Protobuf"), "skill"),
    TaxonomyEntry(r"microservices|microservice\s+architecture", "microservices", "Microservices", ("Microservices", "Microservice Architecture", "Service-Oriented Architecture"), "keyword"),
    TaxonomyEntry(r"distributed\s+systems?", "distributed_systems", "Distributed Systems", ("Distributed Systems", "High Concurrency", "Fault Tolerance"), "keyword"),
    TaxonomyEntry(r"kafka|apache\s+kafka", "kafka", "Apache Kafka", ("Kafka", "Apache Kafka", "Event Streaming"), "skill"),
    TaxonomyEntry(r"rabbitmq", "rabbitmq", "RabbitMQ", ("RabbitMQ", "Message Broker"), "skill"),
    TaxonomyEntry(r"websockets?", "websockets", "WebSockets", ("WebSocket", "WebSockets", "Real-time Messaging"), "skill"),
    TaxonomyEntry(r"system\s+design", "system_design", "System Design", ("System Design", "Scalability", "High Availability"), "keyword"),

    # Testing
    TaxonomyEntry(r"pytest", "pytest", "Pytest", ("Pytest", "Python Testing"), "tooling"),
    TaxonomyEntry(r"jest", "jest", "Jest", ("Jest", "JS Testing"), "tooling"),
    TaxonomyEntry(r"cypress", "cypress", "Cypress", ("Cypress", "E2E Testing"), "tooling"),
    TaxonomyEntry(r"playwright", "playwright", "Playwright", ("Playwright", "Browser Automation"), "tooling"),
    TaxonomyEntry(r"unit\s+testing|integration\s+testing|tdd|test[- ]driven\s+development", "testing", "Automated Testing", ("Unit Testing", "Integration Testing", "TDD", "Test-Driven Development"), "skill"),

    # Soft Skills & Leadership
    TaxonomyEntry(r"communication(?:\s+skills)?", "communication", "Communication", ("Communication", "Verbal Communication", "Written Communication"), "soft_skill"),
    TaxonomyEntry(r"leadership|leading\s+teams?", "leadership", "Leadership", ("Leadership", "Team Leadership", "Technical Leadership"), "soft_skill"),
    TaxonomyEntry(r"mentoring|mentorship", "mentoring", "Mentorship", ("Mentoring", "Mentorship", "Coaching"), "soft_skill"),
    TaxonomyEntry(r"collaboration|cross[- ]functional\s+collaboration|teamwork", "collaboration", "Cross-Functional Collaboration", ("Collaboration", "Teamwork", "Cross-Functional Collaboration"), "soft_skill"),
    TaxonomyEntry(r"problem[- ]solving|critical\s+thinking", "problem_solving", "Problem Solving", ("Problem Solving", "Critical Thinking", "Analytical Skills"), "soft_skill"),
    TaxonomyEntry(r"agile|scrum|kanban", "agile", "Agile / Scrum", ("Agile", "Scrum", "Kanban", "Sprint Planning"), "soft_skill"),

    # Domains
    TaxonomyEntry(r"fintech|financial\s+technology|banking|payments?", "fintech", "Fintech", ("Fintech", "Financial Services", "Banking", "Payments"), "domain_knowledge"),
    TaxonomyEntry(r"healthcare|healthtech|medtech|hipaa", "healthcare", "Healthcare", ("Healthcare", "HealthTech", "MedTech", "HIPAA"), "domain_knowledge"),
    TaxonomyEntry(r"e-?commerce|retail", "ecommerce", "E-Commerce", ("E-Commerce", "eCommerce", "Online Retail"), "domain_knowledge"),
    TaxonomyEntry(r"saas|b2b\s+saas", "saas", "SaaS", ("SaaS", "B2B SaaS", "Software-as-a-Service"), "domain_knowledge"),
    TaxonomyEntry(r"cybersecurity|infosec|security\s+compliance", "cybersecurity", "Cybersecurity", ("Cybersecurity", "InfoSec", "Information Security", "Security"), "domain_knowledge"),
    TaxonomyEntry(r"adtech|advertising\s+technology", "adtech", "AdTech", ("AdTech", "Digital Advertising"), "domain_knowledge"),
    TaxonomyEntry(r"edtech|educational\s+technology", "edtech", "EdTech", ("EdTech", "Education Technology"), "domain_knowledge"),

    # Certifications
    TaxonomyEntry(r"aws\s+certif\w+|aws\s+certified(?:\s+solutions?\s+architect|\s+developer|\s+sysops)?", "aws_cert", "AWS Certification", ("AWS Certified", "AWS Solutions Architect", "AWS Certification"), "certification"),
    TaxonomyEntry(r"gcp\s+certif\w+|google\s+cloud\s+certified", "gcp_cert", "Google Cloud Certification", ("GCP Certified", "Google Cloud Certified"), "certification"),
    TaxonomyEntry(r"azure\s+certif\w+|microsoft\s+certified(?:\s+azure)?", "azure_cert", "Azure Certification", ("Azure Certified", "Microsoft Certified"), "certification"),
    TaxonomyEntry(r"cka|certified\s+kubernetes\s+administrator", "cka_cert", "CKA Certification", ("CKA", "Certified Kubernetes Administrator"), "certification"),
    TaxonomyEntry(r"pmp|project\s+management\s+professional", "pmp_cert", "PMP Certification", ("PMP", "Project Management Professional"), "certification"),
    TaxonomyEntry(r"cissp|certified\s+information\s+systems\s+security\s+professional", "cissp_cert", "CISSP Certification", ("CISSP",), "certification"),
]


# Canonical lookup cache
_CANONICAL_INDEX: dict[str, TaxonomyEntry] = {entry.canonical: entry for entry in TECH_TAXONOMY}


def normalize_skill_name(raw_name: str) -> str:
    """Normalize an arbitrary raw skill string into a canonical slug format."""
    clean = raw_name.strip().lower()
    # Check taxonomy direct matches
    for entry in TECH_TAXONOMY:
        if re.fullmatch(rf"(?:{entry.pattern})", clean, re.IGNORECASE):
            return entry.canonical
        for synonym in entry.synonyms:
            if synonym.lower() == clean:
                return entry.canonical

    # Fallback normalization: replace dots/slashes/spaces with underscores, strip non-alphanumeric
    normalized = re.sub(r"[\s\-/.]+", "_", clean)
    normalized = re.sub(r"[^\w_]", "", normalized).strip("_")
    return normalized or clean


def get_synonyms_for_canonical(canonical: str) -> list[str]:
    """Retrieve synonym list for a canonical identifier."""
    if canonical in _CANONICAL_INDEX:
        return list(_CANONICAL_INDEX[canonical].synonyms)
    return [canonical.replace("_", " ").title(), canonical]
