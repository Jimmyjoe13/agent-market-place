"""
GitHub Provider
================

Provider pour l'extraction de données depuis les repositories GitHub.
Utilise PyGithub pour accéder à l'API GitHub.
"""

from collections.abc import Iterator

from github import Github, GithubException
from github.Repository import Repository

from src.config.settings import get_settings
from src.models.document import SourceType
from src.providers.base import BaseProvider, ExtractedContent


class GithubProvider(BaseProvider):
    """
    Provider pour l'extraction de données GitHub.

    Extrait les README, fichiers de code et documentation
    depuis les repositories GitHub.

    Attributes:
        client: Client PyGithub authentifié.
        extensions: Extensions de fichiers à extraire.
    """

    # Extensions de fichiers à extraire par défaut
    DEFAULT_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".md",
        ".rst",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
    }

    # Fichiers à ignorer
    IGNORE_PATTERNS = {
        "node_modules",
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "dist",
        "build",
    }

    def __init__(
        self,
        extensions: set[str] | None = None,
        max_file_size: int = 100000,
    ) -> None:
        """
        Initialise le provider GitHub.

        Args:
            extensions: Extensions à extraire (défaut: code + docs).
            max_file_size: Taille max des fichiers en bytes.
        """
        settings = get_settings()
        token = settings.github_access_token

        self._client = Github(token) if token else Github()
        self.extensions = extensions or self.DEFAULT_EXTENSIONS
        self.max_file_size = max_file_size

    @property
    def source_type(self) -> SourceType:
        """Type de source: GitHub."""
        return SourceType.GITHUB

    def extract(self, source: str) -> Iterator[ExtractedContent]:
        """
        Extrait le contenu d'un repository GitHub.

        Args:
            source: Nom du repo (format: owner/repo) ou URL complète.

        Yields:
            ExtractedContent pour chaque fichier extrait.
        """
        repo_name = self._parse_repo_name(source)

        try:
            repo = self._client.get_repo(repo_name)
            self.logger.info("Extracting repository", repo=repo_name)

            # Extraire le README en priorité
            yield from self._extract_readme(repo)

            # Extraire les fichiers de code
            yield from self._extract_files(repo)

        except GithubException as e:
            self.logger.error(
                "GitHub API error",
                repo=repo_name,
                status=e.status,
                message=e.data.get("message", str(e)),
            )
            raise

    def _parse_repo_name(self, source: str) -> str:
        """Parse le nom du repository depuis une URL ou un nom."""
        if source.startswith("https://github.com/"):
            # Format: https://github.com/owner/repo
            parts = source.replace("https://github.com/", "").split("/")
            return f"{parts[0]}/{parts[1]}"
        return source

    def _extract_readme(self, repo: Repository) -> Iterator[ExtractedContent]:
        """Extrait le README du repository."""
        try:
            readme = repo.get_readme()
            content = readme.decoded_content.decode("utf-8")

            yield ExtractedContent(
                content=content,
                source_id=f"github:{repo.full_name}:README",
                metadata={
                    "title": f"README - {repo.name}",
                    "url": readme.html_url,
                    "author": repo.owner.login,
                    "language": "markdown",
                    "tags": ["readme", "documentation"],
                    "extra": {
                        "repo": repo.full_name,
                        "stars": repo.stargazers_count,
                        "description": repo.description,
                    },
                },
            )
            self.logger.info("README extracted", repo=repo.full_name)

        except GithubException:
            self.logger.warning("No README found", repo=repo.full_name)

    def _extract_files(
        self,
        repo: Repository,
        path: str = "",
    ) -> Iterator[ExtractedContent]:
        """Extrait les fichiers de code récursivement."""
        try:
            contents = repo.get_contents(path)

            if not isinstance(contents, list):
                contents = [contents]

            for content in contents:
                # Ignorer les dossiers blacklistés
                if any(p in content.path for p in self.IGNORE_PATTERNS):
                    continue

                if content.type == "dir":
                    yield from self._extract_files(repo, content.path)

                elif content.type == "file":
                    # Vérifier l'extension
                    ext = "." + content.name.split(".")[-1] if "." in content.name else ""
                    if ext not in self.extensions:
                        continue

                    # Vérifier la taille
                    if content.size > self.max_file_size:
                        self.logger.debug(
                            "File too large, skipping",
                            file=content.path,
                            size=content.size,
                        )
                        continue

                    try:
                        file_content = content.decoded_content.decode("utf-8")

                        yield ExtractedContent(
                            content=file_content,
                            source_id=f"github:{repo.full_name}:{content.path}",
                            metadata={
                                "title": content.name,
                                "url": content.html_url,
                                "file_path": content.path,
                                "language": self._detect_language(ext),
                                "tags": ["code", repo.language or "unknown"],
                                "extra": {
                                    "repo": repo.full_name,
                                    "size": content.size,
                                    "sha": content.sha,
                                },
                            },
                        )
                    except Exception as e:
                        self.logger.warning(
                            "Failed to decode file",
                            file=content.path,
                            error=str(e),
                        )

        except GithubException as e:
            self.logger.warning(
                "Failed to list contents",
                path=path,
                error=str(e),
            )

    @staticmethod
    def _detect_language(ext: str) -> str:
        """Détecte le langage depuis l'extension."""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".rst": "rst",
        }
        return mapping.get(ext, "text")

    def get_user_repos(self, username: str) -> list[str]:
        """
        Liste les repositories publics d'un utilisateur.

        Args:
            username: Nom d'utilisateur GitHub.

        Returns:
            Liste des noms de repositories (format owner/repo).
        """
        try:
            user = self._client.get_user(username)
            return [repo.full_name for repo in user.get_repos()]
        except GithubException as e:
            self.logger.error("Failed to get user repos", error=str(e))
            return []
