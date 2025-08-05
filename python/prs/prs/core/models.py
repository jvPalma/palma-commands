class PullRequest:
    """
    Domain model for a Pull Request.
    """

    def __init__(
        self,
        id: int,
        title: str,
        author: str,
        labels: list[str],
        checks: list[dict],
        reviews: list[dict],
        url: str,
        branch: str,
        is_draft: bool,
        role: str = None,
        review_requests: list[dict] = None,
        raw_data: dict = None,
    ):
        self.id = id
        self.title = title
        self.author = author
        self.labels = labels
        self.checks = checks
        self.reviews = reviews
        self.review_requests = review_requests if review_requests is not None else []
        self.url = url
        self.branch = branch
        self.is_draft = is_draft
        self.role = role  # Values: 'author', 'reviewer_pending', 'reviewer_completed', 'both_pending', 'both_completed'
        self.raw_data = raw_data if raw_data is not None else {}

        # For internal usage, e.g., 'authored', 'team', 'review_requested'
        self.source = None
        
        # Compatibility property for legacy code
        self.isDraft = is_draft

    def summary(self) -> str:
        return f"[#{self.id}] {self.title} by {self.author}"
