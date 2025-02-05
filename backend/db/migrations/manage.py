# db/migrations/manage.py
import click
from alembic.config import Config
from alembic import command

@click.group()
def cli():
    pass

@cli.command()
def init():
    """Initialize migrations"""
    alembic_cfg = Config("alembic.ini")
    command.init(alembic_cfg, "migrations")

@cli.command()
@click.option('--message', '-m', help='Migration message')
def migrate(message):
    """Create a new migration"""
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=True)

@cli.command()
def upgrade():
    """Upgrade to latest revision"""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

@cli.command()
def downgrade():
    """Downgrade one revision"""
    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, "-1")

if __name__ == '__main__':
    cli()