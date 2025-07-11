"""
Detail screen for viewing comprehensive PR information.

Provides full-screen detailed view of a single pull request with
tabbed navigation for different information types.
"""

from typing import Optional
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, Tabs
from textual.widgets import Static, TabbedContent, TabPane, DataTable, Log, Tree
from textual.reactive import reactive
from textual.binding import Binding

from ..widgets.header import HeaderWidget
from ..widgets.footer import FooterWidget
from ...core.models import PullRequest


class DetailScreen(Screen):
    """
    Full-screen detail view for a pull request.
    
    Layout:
    ┌─────────────────────────────────────────────────┐
    │ Header (repo info, PR title)                   │
    ├─────────────────────────────────────────────────┤
    │ [Overview] [Checks] [Reviews] [Comments] [...]  │
    ├─────────────────────────────────────────────────┤
    │                                                 │
    │              Tab Content Area                   │
    │                                                 │
    │                                                 │
    │                                                 │
    ├─────────────────────────────────────────────────┤
    │ Footer (navigation, actions)                    │
    └─────────────────────────────────────────────────┘
    """
    
    CSS = """
    DetailScreen {
        layout: grid;
        grid-size: 1 4;
        grid-rows: auto auto 1fr auto;
    }
    
    #header {
        height: 3;
    }
    
    #tab-content {
        border: solid $primary;
    }
    
    #footer {
        height: 2;
    }
    
    .overview-section {
        margin: 1;
        padding: 1;
        border: solid $secondary;
    }
    
    .status-grid {
        layout: grid;
        grid-size: 3 2;
        grid-gutter: 1;
        margin: 1;
    }
    
    .status-card {
        border: solid $accent;
        padding: 1;
        text-align: center;
    }
    """
    
    BINDINGS = [
        Binding("escape,q", "back", "Back", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("o", "open_browser", "Browser", show=True),
        Binding("c", "copy_url", "Copy URL", show=True),
        Binding("tab", "next_tab", "Next Tab", show=False),
        Binding("shift+tab", "prev_tab", "Prev Tab", show=False),
        Binding("1", "tab_overview", "Overview", show=False),
        Binding("2", "tab_checks", "Checks", show=False),
        Binding("3", "tab_reviews", "Reviews", show=False),
        Binding("4", "tab_comments", "Comments", show=False),
        Binding("5", "tab_commits", "Commits", show=False),
        Binding("6", "tab_files", "Files", show=False),
    ]
    
    def __init__(self, pr: PullRequest, **kwargs):
        super().__init__(**kwargs)
        self.pr = pr
        self.current_tab = "overview"
    
    def compose(self):
        """Compose the detail screen layout."""
        yield HeaderWidget(id="header")
        
        with TabbedContent(id="tab-content"):
            with TabPane("Overview", id="overview"):
                yield self.create_overview_content()
            
            with TabPane("Checks", id="checks"):
                yield self.create_checks_content()
            
            with TabPane("Reviews", id="reviews"):
                yield self.create_reviews_content()
            
            with TabPane("Comments", id="comments"):
                yield self.create_comments_content()
            
            with TabPane("Commits", id="commits"):
                yield self.create_commits_content()
            
            with TabPane("Files", id="files"):
                yield self.create_files_content()
        
        yield FooterWidget(id="footer")
    
    def on_mount(self) -> None:
        """Initialize the detail screen."""
        # Update header with PR info
        header = self.query_one("#header", HeaderWidget)
        header.repo_name = f"PR #{self.pr.id}"
        header.owner = self.pr.title
    
    def create_overview_content(self) -> Container:
        """Create overview tab content."""
        container = Container()
        
        with container:
            # PR metadata
            with Container(classes="overview-section"):
                yield Static(f"[bold]Title:[/bold] {self.pr.title}")
                yield Static(f"[bold]Author:[/bold] {self.pr.author}")
                yield Static(f"[bold]Branch:[/bold] {self.pr.branch}")
                yield Static(f"[bold]State:[/bold] {self.pr.state}")
                if self.pr.is_draft:
                    yield Static("[bold]Status:[/bold] [yellow]Draft[/yellow]")
                if self.pr.created_at:
                    yield Static(f"[bold]Created:[/bold] {self.pr.created_at}")
                if self.pr.updated_at:
                    yield Static(f"[bold]Updated:[/bold] {self.pr.updated_at}")
            
            # Statistics
            with Container(classes="status-grid"):
                yield Container(
                    Static(f"[bold cyan]{self.pr.additions}[/bold cyan]"),
                    Static("Additions"),
                    classes="status-card"
                )
                yield Container(
                    Static(f"[bold red]{self.pr.deletions}[/bold red]"),
                    Static("Deletions"),
                    classes="status-card"
                )
                yield Container(
                    Static(f"[bold]{self.pr.changed_files}[/bold]"),
                    Static("Files"),
                    classes="status-card"
                )
                yield Container(
                    Static(f"[bold]{len(self.pr.commits)}[/bold]"),
                    Static("Commits"),
                    classes="status-card"
                )
                yield Container(
                    Static(f"[bold]{len(self.pr.reviews)}[/bold]"),
                    Static("Reviews"),
                    classes="status-card"
                )
                yield Container(
                    Static(f"[bold]{len(self.pr.checks)}[/bold]"),
                    Static("Checks"),
                    classes="status-card"
                )
            
            # Labels
            if self.pr.labels:
                with Container(classes="overview-section"):
                    yield Static("[bold]Labels:[/bold]")
                    labels_text = ", ".join([f"[blue]{label}[/blue]" for label in self.pr.labels])
                    yield Static(labels_text)
            
            # URL
            with Container(classes="overview-section"):
                yield Static(f"[bold]URL:[/bold] [link={self.pr.url}]{self.pr.url}[/link]")
        
        return container
    
    def create_checks_content(self) -> DataTable:
        """Create checks tab content."""
        table = DataTable()
        table.add_columns("Status", "Name", "Conclusion", "Description")
        
        for check in self.pr.checks:
            status_icon = "✅" if check.get('status') == 'completed' and check.get('conclusion') == 'success' else "❌"
            if check.get('status') == 'in_progress':
                status_icon = "⏳"
            
            table.add_row(
                status_icon,
                check.get('name', 'Unknown'),
                check.get('conclusion', check.get('status', 'unknown')),
                check.get('description', '')
            )
        
        if not self.pr.checks:
            table.add_row("", "No checks found", "", "")
        
        return table
    
    def create_reviews_content(self) -> DataTable:
        """Create reviews tab content."""
        table = DataTable()
        table.add_columns("Status", "Reviewer", "State", "Submitted")
        
        for review in self.pr.reviews:
            state = review.get('state', 'unknown')
            status_icon = {
                'approved': '✅',
                'changes_requested': '❌',
                'commented': '💬',
                'dismissed': '🚫'
            }.get(state.lower(), '❓')
            
            reviewer = review.get('user', {}).get('login', 'Unknown')
            submitted_at = review.get('submitted_at', '')
            
            table.add_row(
                status_icon,
                reviewer,
                state,
                submitted_at
            )
        
        if not self.pr.reviews:
            table.add_row("", "No reviews found", "", "")
        
        return table
    
    def create_comments_content(self) -> Log:
        """Create comments tab content."""
        log = Log()
        
        for comment in self.pr.comments:
            author = comment.get('user', {}).get('login', 'Unknown')
            body = comment.get('body', '')
            created_at = comment.get('created_at', '')
            
            log.write_line(f"[bold cyan]{author}[/bold cyan] - {created_at}")
            log.write_line(body)
            log.write_line("")
        
        if not self.pr.comments:
            log.write_line("No comments found")
        
        return log
    
    def create_commits_content(self) -> DataTable:
        """Create commits tab content."""
        table = DataTable()
        table.add_columns("SHA", "Message", "Author", "Date")
        
        for commit in self.pr.commits:
            sha = commit.get('sha', '')[:8]
            message = commit.get('commit', {}).get('message', '').split('\n')[0]
            author = commit.get('commit', {}).get('author', {}).get('name', 'Unknown')
            date = commit.get('commit', {}).get('author', {}).get('date', '')
            
            table.add_row(sha, message, author, date)
        
        if not self.pr.commits:
            table.add_row("", "No commits found", "", "")
        
        return table
    
    def create_files_content(self) -> Static:
        """Create files tab content."""
        # This would require additional API calls to get file changes
        # For now, show a placeholder
        return Static(
            f"[dim]File changes not loaded.[/dim]\n"
            f"[dim]Files changed: {self.pr.changed_files}[/dim]\n"
            f"[dim]Additions: +{self.pr.additions}[/dim]\n"
            f"[dim]Deletions: -{self.pr.deletions}[/dim]"
        )
    
    def on_tabbed_content_tab_activated(self, message: TabbedContent.TabActivated) -> None:
        """Handle tab changes."""
        self.current_tab = message.tab.id
    
    # Action handlers
    def action_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()
    
    def action_refresh(self) -> None:
        """Refresh PR data."""
        # TODO: Implement refresh logic
        pass
    
    def action_open_browser(self) -> None:
        """Open PR in browser."""
        import webbrowser
        try:
            webbrowser.open(self.pr.url)
        except Exception:
            pass
    
    def action_copy_url(self) -> None:
        """Copy PR URL to clipboard."""
        import pyperclip
        try:
            pyperclip.copy(self.pr.url)
        except Exception:
            pass
    
    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one(TabbedContent)
        tabs.next_tab()
    
    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        tabs = self.query_one(TabbedContent)
        tabs.previous_tab()
    
    def action_tab_overview(self) -> None:
        """Switch to overview tab."""
        tabs = self.query_one(TabbedContent)
        tabs.active = "overview"
    
    def action_tab_checks(self) -> None:
        """Switch to checks tab."""
        tabs = self.query_one(TabbedContent)
        tabs.active = "checks"
    
    def action_tab_reviews(self) -> None:
        """Switch to reviews tab."""
        tabs = self.query_one(TabbedContent)
        tabs.active = "reviews"
    
    def action_tab_comments(self) -> None:
        """Switch to comments tab."""
        tabs = self.query_one(TabbedContent)
        tabs.active = "comments"
    
    def action_tab_commits(self) -> None:
        """Switch to commits tab."""
        tabs = self.query_one(TabbedContent)
        tabs.active = "commits"
    
    def action_tab_files(self) -> None:
        """Switch to files tab."""
        tabs = self.query_one(TabbedContent)
        tabs.active = "files"