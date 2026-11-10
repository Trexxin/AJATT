# AJATT

A retrieval-augmented question-answering system built on the archive of the All Japanese All
The Time blog. Ask a question about learning Japanese in English and get an answer grounded
in retrieved blog excerpts, with links to the source posts.

The project has two stages:

1. The scraper downloads and parses the blog into structured JSON.
2. The RAG prototype chunks that JSON, builds dense and BM25 indexes, retrieves relevant
   excerpts, and sends them to an OpenAI-compatible chat-completions endpoint.

## Requirements

- Python 3.10 or newer
- Network access to the HPC LLM endpoint for answer generation
- The dependencies in `prototype/requirements.txt`

Run all commands below from the repository root (`AJATT`), not from `prototype/`. The scripts
use paths relative to the repository root.

## 1. Set up the environment

Create and activate a virtual environment, then install the prototype dependencies:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r prototype\requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r prototype/requirements.txt
```

## 2. Get and parse the blog data

The original site is down. A community-run copy is available at
<https://alljapanesealltheti.me/blog/> and is served from the
[all-japanese-all-the-time repository](https://github.com/all-japanese-all-the-time/all-japanese-all-time).

Download posts:

```bash
python scraper/scrape.py --limit 20               # optional quick test
python scraper/scrape.py                          # crawl the whole site
python scraper/scrape.py --from-dir path/to/copy  # use a local site copy
```

Parse the downloaded HTML into JSONL:

```bash
python scraper/parse.py
```

This creates `data/processed/posts.jsonl`, which is the input consumed by the RAG indexer.
Downloaded HTML is stored under `data/raw/posts/`. Existing downloads are skipped, so an
interrupted scrape can be resumed.

## 3. Build the retrieval indexes

Run the index script after parsing the posts:

```bash
python prototype/index.py
```

The script chunks the posts and creates:

- `prototype/faiss.index`: dense vector index using
  `sentence-transformers/all-MiniLM-L6-v2`
- `prototype/bm25.pkl`: sparse BM25 index and chunk metadata
- `prototype/chunks.json`: serialized chunks for lookup and inspection

Re-run this command whenever `data/processed/posts.jsonl` changes. The first run downloads
the embedding model and may take several minutes.

## 4. Test retrieval without the LLM

Once the index files exist, run the retrieval smoke test:

```bash
python prototype/retrieve.py
```

It searches for a sample question and prints the top matching excerpts and their reciprocal
rank-fusion scores. The `retrieve` function can also be imported by code that runs with
`prototype/` on its Python path.

## 5. Configure the LLM endpoint

The generator uses the OpenAI-compatible `/v1/chat/completions` endpoint hosted on the HPC
node. Set these variables in the same shell used to run the pipeline:

Windows PowerShell:

```powershell
$env:LLM_BASE_URL = "http://dh-dgxh100-2.hpc.msoe.edu:8000/v1"
$env:LLM_MODEL = "meta/llama-4-scout-17b-16e-instruct"
```

macOS/Linux:

```bash
export LLM_BASE_URL="http://dh-dgxh100-2.hpc.msoe.edu:8000/v1"
export LLM_MODEL="meta/llama-4-scout-17b-16e-instruct"
```

You must be on the network that can resolve and reach `dh-dgxh100-2.hpc.msoe.edu`. Any variables needed can also be placed in a `.env` file at the repository root.

## 6. Run the RAG pipeline

Run the built-in sample questions:

```bash
python prototype/pipeline.py
```

For each question, the pipeline retrieves the top passages, builds a citation-focused prompt,
calls the configured chat-completions endpoint, and prints the answer and source posts.

To call it from another Python program:

```python
from prototype.pipeline import ask

answer, sources = ask("How should I use an SRS?", top_k=10)
print(answer)
for source in sources:
    print(source["title"], source["url"])
```

## 7. Run the evaluation

Create `prototype/eval_questions.json` with evaluation items in this format:

```json
[
  {
    "question": "What is sentence mining?",
    "ground_truth": "The expected answer based on the AJATT archive."
  }
]
```

Then run:

```bash
python prototype/evaluate.py
```

The evaluation script runs every question through the same retrieval and generation pipeline
and reports the RAGAS `faithfulness`, `answer_relevancy`, and `context_precision` metrics.
The LLM endpoint must be configured and reachable because evaluation generates an answer for
each item.

## Project layout

| Path | Purpose |
|---|---|
| `scraper/` | Download and parse the blog archive |
| `data/processed/posts.jsonl` | Parsed post records used by chunking |
| `prototype/chunk.py` | Normalize posts and create overlapping chunks |
| `prototype/index.py` | Build FAISS and BM25 indexes |
| `prototype/retrieve.py` | Hybrid dense/sparse retrieval with reciprocal rank fusion |
| `prototype/generate.py` | OpenAI-compatible LLM client and grounded prompt |
| `prototype/pipeline.py` | Retrieval plus answer generation |
| `prototype/evaluate.py` | RAGAS evaluation |
