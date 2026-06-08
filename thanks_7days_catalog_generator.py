name: Update Thanks 7DAYS Catalog

on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install requests

      - run: python thanks_7days_catalog_generator.py

      - name: Commit updated index.html
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add index.html
          git commit -m "Update THANKS 7DAYS catalog" || echo "No changes"
          git push
