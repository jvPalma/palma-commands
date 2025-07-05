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
        comments: list[dict],
        url: str,
        branch: str,
        is_draft: bool,
        additions: int = 0,
        deletions: int = 0,
        changed_files: int = 0,
        created_at: str = None,
        updated_at: str = None,
        state: str = "open",
        commits: list[dict] = None,
        merged: bool = False,
        merged_at: str = None,
        closed_at: str = None,
        merged_by: dict = None,
    ):
        self.id = id
        self.title = title
        self.author = author
        self.labels = labels
        self.checks = checks
        self.reviews = reviews
        self.comments = comments
        self.url = url
        self.branch = branch
        self.is_draft = is_draft
        self.additions = additions
        self.deletions = deletions
        self.changed_files = changed_files
        self.created_at = created_at
        self.updated_at = updated_at
        self.state = state
        self.commits = commits if commits is not None else []
        self.merged = merged
        self.merged_at = merged_at
        self.closed_at = closed_at
        self.merged_by = merged_by

        # For internal usage, e.g., 'authored', 'team', 'review_requested'
        self.source = None

    def summary(self) -> str:
        return f"[#{self.id}] {self.title} by {self.author}"
