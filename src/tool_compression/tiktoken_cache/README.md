# Local tokenizer cache

These two files are the public BPE rank tables used by tiktoken 0.14.0 for `o200k_base` and `cl100k_base`. The filename is the SHA-1 of the public URL, which is tiktoken's cache key. The file bytes match the hashes published in `tiktoken_ext.openai_public`.

The offline amendment reads this directory and does not fetch the tables again. `o200k_base` chooses nothing in the editor; it only counts local tokens. `cl100k_base` is a recount and is not used to choose an edit.
