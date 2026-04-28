import typer

app = typer.Typer(help="Manage external Codex skills and aliases.")


@app.callback()
def main() -> None:
    """Manage external Codex skills and aliases."""
