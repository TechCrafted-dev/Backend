from enum import Enum
from typing import Any, Dict, List


class Tags(str, Enum):
    state = "States"
    github = "GitHub"
    github_orgs = "GitHub Orgs"
    repos = "Repositories"
    post = "Post"
    news = "News"

TAG_DESCRIPTIONS: Dict[str, str] = {
    Tags.state.value:       "API health and resources.",
    Tags.github.value:      "Operations on the GitHub user.",
    Tags.github_orgs.value: "Consultation of user organizations on GitHub.",
    Tags.repos.value:       "Repository CRUD.",
    Tags.post.value:        "Posts generated from repositories.",
    Tags.news.value:        "Search and publication of news.",
}

tags_metadata: List[Dict[str, Any]] = [
    {
        "name": tag.value,
        "description": TAG_DESCRIPTIONS.get(tag.value),
    }
    for tag in Tags
]

class OrderField(str, Enum):
    id = "id"
    name = "name"
    created_at = "created_at"
    updated_at = "updated_at"

class OrderDirection(str, Enum):
    asc = "asc"
    desc = "desc"
