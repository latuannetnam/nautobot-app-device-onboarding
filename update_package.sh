echo "Updating netnam-cms-core package from private repository..."
poetry update netnam-cms-core
poetry lock
poetry install
invoke build