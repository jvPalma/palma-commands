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
    ):
        self.id = id
        self.title = title
        self.author = author
        self.labels = labels
        self.checks = checks
        self.reviews = reviews
        self.url = url
        self.branch = branch
        self.is_draft = is_draft

        # For internal usage, e.g., 'authored', 'team', 'review_requested'
        self.source = None

    def summary(self) -> str:
        return f"[#{self.id}] {self.title} by {self.author}"
