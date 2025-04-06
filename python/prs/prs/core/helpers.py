from prs.config import get


def resolve_owner():
    """
    Determines who is the 'owner' of the repository according to the config:
    - if 'username' => use git.username
    - if 'org_name' => use git-org.org_name
    - otherwise => use literal value
    """
    upstream_config = get(
        "git", "upstream"
    )  # ex: 'username' or 'org_name' or 'whatever'
    user_conf = get("git", "username")
    org_conf = get("git-org", "org_name")

    if upstream_config == "username":
        return user_conf
    elif upstream_config == "org_name":
        return org_conf
    else:
        return upstream_config


def read_authors():
    authors_str = get("pr-info", "authors", fallback="")

    if not authors_str.strip():
        # fallback to the git.username config
        return [get("git", "username")]
    else:
        # ex: "user-1, user-2, user-3"
        authors_list = authors_str.split(",")
        # clean up spaces
        return [a.strip() for a in authors_list if a.strip()]
