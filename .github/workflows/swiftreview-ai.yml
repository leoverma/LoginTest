name: SwiftReview AI (GROQ)

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
  workflow_dispatch: {}

jobs:
  swiftreview:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      pull-requests: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: |
          pip install requests groq || pip install requests

      - name: Run SwiftReview AI (GROQ)
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GROQ_MODEL: "llama3.1-70b"          # change to a model you have access to
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          python tools/swiftreview/github_layer.py
